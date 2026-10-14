"""Pinned image-to-component inference; no dataset or target CAD dependency."""
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from safetensors.torch import load_file
from transformers import AutoModel

from img2dwg.graph_decoder import SharedGraphDecoder, decode
from img2dwg.graph_constraints import project
from img2dwg.structured import compile_graph


def normalize(image, size=512):
    image = ImageOps.exif_transpose(image)
    if 'A' in image.getbands():
        base = Image.new('RGBA', image.size, 'white')
        image = Image.alpha_composite(base, image.convert('RGBA'))
    image = image.convert('RGB')
    original = image.size
    fitted = ImageOps.contain(image, (size - 48, size - 48), Image.Resampling.LANCZOS)
    offset = ((size - fitted.width) // 2, (size - fitted.height) // 2)
    canvas = Image.new('RGB', (size, size), 'white')
    canvas.paste(fitted, offset)
    return canvas, {'original_size': original, 'fitted_size': fitted.size,
                    'offset': offset, 'exif_orientation_applied': True}


@torch.inference_mode()
def image_features(encoder, canvas):
    # Identical to the real-image trainer: ImageNet normalization, 512 input,
    # last 32x32 patch tokens, pooled 16x16 observation features.
    x = torch.from_numpy(np.asarray(canvas, np.float32).transpose(2, 0, 1).copy() / 255)[None]
    x = (x - x.new_tensor([.485, .456, .406])[None, :, None, None]) / x.new_tensor([.229, .224, .225])[None, :, None, None]
    grid = canvas.width // 16
    tokens = encoder(pixel_values=x).last_hidden_state[:, -(grid ** 2):]
    pooled = torch.nn.functional.adaptive_avg_pool2d(tokens.transpose(1, 2).reshape(1, 768, grid, grid), (16, 16))
    return pooled.flatten(2).transpose(1, 2).contiguous()


def load(folder, expected_sha):
    folder = Path(folder)
    sha = hashlib.sha256((folder / 'model.safetensors').read_bytes()).hexdigest()
    if not expected_sha or sha != expected_sha:
        raise ValueError('Pinned shared checkpoint hash mismatch')
    config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
    library = json.loads((folder / 'library.json').read_text(encoding='utf-8'))
    release = json.loads((folder / 'release.json').read_text(encoding='utf-8'))
    for name in ('config.json', 'library.json'):
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != release['files'][name]:
            raise ValueError('Release metadata hash mismatch: ' + name)
    model = SharedGraphDecoder(config['nodes'], config['components'], len(config['texts']),
        hidden=config['hidden'], templates=config['templates'],
        coord_digits=config.get('coord_digits', 6), measure_digits=config.get('measure_digits', 5),
        adaptive_capacity=config.get('adaptive_capacity', False),
        minimum_nodes=config.get('minimum_nodes', 32), minimum_components=config.get('minimum_components', 32))
    state = load_file(str(folder / 'model.safetensors'))
    # The tiny v3 checkpoint predates the full-data count heads. Its query
    # capacity is fixed; omit only these unused heads and reject other drift.
    result = model.load_state_dict(state, strict=False)
    if result.unexpected_keys or any(not key.startswith('count.') for key in result.missing_keys):
        raise ValueError('Checkpoint architecture mismatch: ' + str(result))
    if result.missing_keys and config.get('adaptive_capacity', False):
        raise ValueError('Adaptive inference requires trained count heads')
    model.eval()
    encoder = AutoModel.from_pretrained(config['backbone'], revision=config['backbone_revision']).eval()
    encoder.requires_grad_(False)
    return model, encoder, config, library, release


@torch.inference_mode()
def predict(loaded, image, round_lengths=False):
    model, encoder, config, library, release = loaded
    start = time.perf_counter()
    canvas, transform = normalize(image, config['size'])
    features = image_features(encoder, canvas)
    raw = decode(model(features), config['texts'], threshold=config['threshold'], templates=library)
    solved = project(raw)
    if round_lengths:
        from img2dwg.graph_constraints import snap_major_lengths
        solved = snap_major_lengths(solved)
    graph = compile_graph(solved, strict=False)
    graph.update(model_sha256=release['model_sha256'], input_transform=transform,
        normalized_input_pixels_sha256=hashlib.sha256(canvas.tobytes()).hexdigest(),
        model_status=release['deployment_role'], numeric_dimensions_verified=False,
        scale_authority='learned-canonical-mm;human-review-required',
        elapsed_seconds=time.perf_counter() - start)
    return graph, solved, raw
