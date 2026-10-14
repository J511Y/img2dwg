"""Bounded real-pair experiment: train only five, then evaluate five and twenty."""
import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from PIL import Image
from safetensors.torch import save_file, load_file
from transformers import AutoModel
from img2dwg.model import BACKBONE, REVISION
from img2dwg.raw_model import CanonicalDecoder, encode_target, raw_loss, decode_raw
from img2dwg.raw_evaluation import PROTOCOL, evaluate_case, aggregate
from img2dwg.vector import exports
from img2dwg.dimension_solver import constrain_dimensions


@torch.no_grad()
def features(encoder, path, device):
    image = Image.open(path).convert('RGB')
    x = torch.from_numpy(np.asarray(image, np.float32).transpose(2, 0, 1).copy() / 255)[None].to(device)
    x = (x - x.new_tensor([.485, .456, .406])[None, :, None, None]) / x.new_tensor([.229, .224, .225])[None, :, None, None]
    tokens = encoder(pixel_values=x).last_hidden_state[:, -(image.width // 16) ** 2:]
    grid = image.width // 16
    pooled = torch.nn.functional.adaptive_avg_pool2d(tokens.transpose(1, 2).reshape(1, 768, grid, grid), (16, 16))
    # Cached frozen image features are observations, not target-dependent retrieval.
    return pooled.flatten(2).transpose(1, 2).contiguous().clone()


def evaluate(model, encoder, records, root, output, device, training_features=None, solve_dimensions=False):
    model.eval(); rows = []
    for row in records:
        key = row['sample_id']; folder = output / key
        ft = training_features[key] if training_features is not None else features(encoder, root / key / 'input.png', device)
        with torch.inference_mode():
            graph = decode_raw(model(ft), 512, .5)
        raw_graph = graph
        if solve_dimensions:
            graph = constrain_dimensions(graph)
        graph.update(sample_id=key, split=row['split'])
        target = json.loads((root / key / 'target.json').read_text(encoding='utf-8'))
        error = None
        try:
            factory = exports(graph, folder)
        except Exception as exc:
            factory = None; error = str(exc); folder.mkdir(parents=True, exist_ok=True)
            (folder / 'prediction.json').write_text(json.dumps(graph), encoding='utf-8')
        result = evaluate_case(graph, target, factory)
        if solve_dimensions:
            before = exports(raw_graph, folder / 'pre-solver')
            result['before_solver'] = evaluate_case(raw_graph, target, before)
        result.update(sample_id=key, split=row['split'], export_error=error)
        (folder / 'metrics.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        rows.append(result)
        print(json.dumps({'evaluated': key, 'split': row['split'], 'structure_f1': result['structure_f1'],
                          'dimension_missing_or_incorrect': result['components']['dimension']['missing_or_incorrect']}), flush=True)
    return {'aggregate': aggregate(rows), 'rows': rows}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--steps', type=int, default=12000); p.add_argument('--lr', type=float, default=.0005)
    p.add_argument('--seed', type=int, default=20261014); p.add_argument('--model-repo')
    p.add_argument('--resume', type=Path); p.add_argument('--joint-batch', action='store_true')
    p.add_argument('--physical-weight', type=float, default=0); p.add_argument('--solve-dimensions', action='store_true')
    p.add_argument('--freeze-scale', action='store_true')
    args = p.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.set_num_threads(4)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if device != 'cuda':
        raise RuntimeError('Use the bounded GPU job; no accidental lengthy CPU training')
    rows = json.loads((args.data / 'index.json').read_text())
    training = [r for r in rows if r['split'] == 'train']; validation = [r for r in rows if r['split'] == 'validation']
    assert len(training) == 5 and len(validation) == 20
    assert not ({r['group_id'] for r in training} & {r['group_id'] for r in validation})
    for r in rows:
        for name, key in [('input.png', 'input_sha256'), ('target.json', 'target_sha256')]:
            assert hashlib.sha256((args.data / r['sample_id'] / name).read_bytes()).hexdigest() == r[key]
    graphs = {r['sample_id']: json.loads((args.data / r['sample_id'] / 'target.json').read_text()) for r in training}
    queries = math.ceil(max(len(g['components']) for g in graphs.values()) / 64) * 64 + 64
    encoder = AutoModel.from_pretrained(BACKBONE, revision=REVISION).to(device).eval()
    encoder.requires_grad_(False)
    bank = {r['sample_id']: features(encoder, args.data / r['sample_id'] / 'input.png', device) for r in training}
    targets = {k: {n: v.to(device) for n, v in encode_target(g, queries, 64).items()} for k, g in graphs.items()}
    model = CanonicalDecoder(queries).to(device)
    if args.resume:
        model.load_state_dict(load_file(str(args.resume)), strict=True)
    if args.freeze_scale:
        if not args.resume:
            raise ValueError('Scale freezing requires a trained initial checkpoint')
        model.scale.requires_grad_(False)
    config = {'schema': 'img2dwg-raw-component-model/v1', 'queries': queries, 'parents': 64,
              'hidden': 192, 'size': 512, 'backbone': BACKBONE, 'backbone_revision': REVISION,
              'threshold': .5, 'protocol': PROTOCOL, 'input_domain': 'real-as-built',
              'dimension_constraint_solver': bool(args.solve_dimensions),
              'input_output_frame': 'separate;no-pixel-alignment-supervision', 'order': 'kind-then-canonical-geometry'}
    (args.output / 'config.json').write_text(json.dumps(config, indent=2))
    manifest = {'train_ids': [r['sample_id'] for r in training], 'validation_ids': [r['sample_id'] for r in validation],
                'seed': args.seed, 'steps': args.steps, 'initial_lr': args.lr,
                'validation_used_for_training_or_selection': False, 'backbone_frozen': True,
                'code_sha256': os.getenv('CODE_SHA256'), 'data_sha256': os.getenv('TRAINING_ARCHIVE_SHA256'),
                'supervision': ['native-dimension-digits', 'typed-canonical-parameters', 'layer-role-candidates',
                                'native-active-instance-membership', 'shared-identical-CAD-endpoints'],
                'training_symbols': sum(sum(c['kind'] == 'symbol' for c in g['components']) for g in graphs.values()),
                'initial_checkpoint_sha256': hashlib.sha256(args.resume.read_bytes()).hexdigest() if args.resume else None,
                'joint_batch': args.joint_batch, 'physical_weight': args.physical_weight,
                'scale_head_frozen_during_refine': args.freeze_scale}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'device': device, 'queries': queries, 'stage': 'real-pair-training', **manifest}), flush=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    started = time.perf_counter(); keys = list(graphs); log = (args.output / 'train.jsonl').open('a')
    def save(step):
        save_file({k: v.detach().cpu().contiguous() for k, v in model.state_dict().items()}, str(args.output / 'model.safetensors'))
        (args.output / 'progress.json').write_text(json.dumps({'steps': step, 'elapsed_seconds': time.perf_counter() - started}))
    for step in range(1, args.steps + 1):
        model.train()
        if (step - 1) % 5 == 0:
            random.shuffle(keys)
        key = keys[(step - 1) % len(keys)]
        if step > args.steps * .7:
            for group in optimizer.param_groups:
                group['lr'] = args.lr * .1
        optimizer.zero_grad(set_to_none=True)
        batch = list(graphs) if args.joint_batch else [key]
        pred = model(torch.cat([bank[k] for k in batch], 0))
        total, details = raw_loss(pred, [targets[k] for k in batch], args.physical_weight)
        if not torch.isfinite(total):
            save(step - 1); raise ValueError('Non-finite loss')
        total.backward(); norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5.)
        if not torch.isfinite(norm):
            save(step - 1); raise ValueError('Non-finite gradient')
        optimizer.step()
        if step == 1 or step % 100 == 0:
            record = {'step': step, 'loss': float(total.detach()), **details, 'elapsed_seconds': time.perf_counter() - started}
            log.write(json.dumps(record) + '\n'); log.flush(); print(json.dumps(record), flush=True)
        if step % 2000 == 0:
            save(step)
    save(args.steps); log.close()
    train_result = evaluate(model, encoder, training, args.data, args.output / 'train-preview', device, bank, args.solve_dimensions)
    # Validation is run once, even if training reproduction fails, to expose failure.
    val_result = evaluate(model, encoder, validation, args.data, args.output / 'validation-preview', device, solve_dimensions=args.solve_dimensions)
    passed = train_result['aggregate']['passed_cases'] == 5 and val_result['aggregate']['passed_cases'] == 20
    evaluation = {'protocol': PROTOCOL, 'train': train_result, 'validation': val_result,
                  'quality_status': 'passed-numeric-baseline' if passed else 'failed-real-input-geometry-or-required-dimensions',
                  'complete_semantic_CAD_validation': False, 'space_release_allowed': bool(passed)}
    (args.output / 'evaluation.json').write_text(json.dumps(evaluation, indent=2))
    receipt = {'status': 'completed', 'model_quality': evaluation['quality_status'], 'space_release_allowed': bool(passed),
               'steps': args.steps, 'elapsed_seconds': time.perf_counter() - started,
               'model_sha256': hashlib.sha256((args.output / 'model.safetensors').read_bytes()).hexdigest(),
               'train': train_result['aggregate'], 'validation': val_result['aggregate']}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2)); print(json.dumps(receipt), flush=True)
    if args.model_repo:
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ['HF_TOKEN']); api.create_repo(args.model_repo, private=True, exist_ok=True)
        api.upload_folder(repo_id=args.model_repo, folder_path=args.output,
                          allow_patterns=['model.safetensors', 'config.json', 'manifest.json', 'receipt.json', 'evaluation.json', 'train.jsonl'],
                          commit_message='Bounded five real-pair training and untouched twenty-case evaluation; no Space release')


if __name__ == '__main__':
    main()
