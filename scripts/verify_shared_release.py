"""Frozen-checkpoint local verification on original pixels; no optimization."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch
from PIL import Image, ImageOps
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from img2dwg.shared_inference import load, predict, normalize
from img2dwg.graph_evaluation import evaluate, PROTOCOL
from img2dwg.raw_evaluation import aggregate
from img2dwg.vector import exports, svg
from img2dwg.structured import compile_graph


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--twenty', action='store_true')
    args = p.parse_args()
    if (args.output / 'receipt.json').exists():
        raise FileExistsError('Verification receipts are immutable')
    args.output.mkdir(parents=True, exist_ok=True)
    release = json.loads((args.checkpoint / 'release.json').read_text())
    rows = json.loads((args.data / 'index.json').read_text())
    source = {r['sample_id']: r for r in [json.loads(line) for line in
        (args.dataset / 'bundle/records.jsonl').read_text(encoding='utf-8').splitlines()]}
    rows = [r for r in rows if r['cohort'] == 'five' or args.twenty and r['cohort'] == 'twenty']
    protocol = {'model_sha256': release['model_sha256'], 'metric': PROTOCOL,
        'inference_files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
            Path('img2dwg').glob('*.py')}, 'sample_ids': [r['sample_id'] for r in rows],
        'optimization': False, 'threshold_or_routing_tuning': False,
        'full_training_executed': False, 'length_rounding': False}
    write(args.output / 'protocol.json', protocol)
    torch.set_num_threads(6)
    loaded = load(args.checkpoint, release['model_sha256'])
    results = {'five': [], 'twenty': []}
    for row in rows:
        key = row['sample_id']; original = source[key]
        image_path = args.dataset / 'cases' / key / original['image_path']
        assert hashlib.sha256(image_path.read_bytes()).hexdigest() == row['original_image_sha256']
        with Image.open(image_path) as im:
            im.seek(original.get('primary_frame_index', 0))
            image = ImageOps.exif_transpose(im).convert('RGB')
        expected = Image.open(args.data / key / 'input.png').convert('RGB')
        canvas, transform = normalize(image, 512)
        assert canvas.tobytes() == expected.tobytes(), 'Serving/training pixel mismatch: ' + key
        graph, shared, raw = predict(loaded, image)
        folder = args.output / (row['cohort'] + '-preview') / key
        factory = exports(graph, folder)
        write(folder / 'shared-graph.json', shared)
        (folder / 'raw.svg').write_text(svg(compile_graph(raw, strict=False)), encoding='utf-8')
        truth = json.loads((args.data / key / 'target.json').read_text(encoding='utf-8'))
        target = json.loads((args.data / key / 'components.json').read_text(encoding='utf-8'))
        metric = evaluate(shared, target, graph, truth, factory)
        metric.update(sample_id=key, split=row['split'], export_error=None,
                      serving_training_pixels_equal=True, elapsed_seconds=graph['elapsed_seconds'])
        write(folder / 'metrics.json', metric)
        # A PNG of original pixels for the authenticated Space upload test,
        # not a canonical CAD render or a precomputed model output.
        if row['cohort'] == 'five':
            image.save(folder / 'upload.png')
            rounded_graph, rounded_shared, _ = predict(loaded, image, round_lengths=True)
            rounded_factory = exports(rounded_graph, folder / 'rounded')
            write(folder / 'rounded/receipt.json', {'factory': rounded_factory,
                'length_edit': rounded_shared['length_edit_receipt']})
        results[row['cohort']].append(metric)
        print(json.dumps({'case': key, 'cohort': row['cohort'], 'passed': metric['passed'],
            'structure_f1': metric['structure_f1'], 'dimensions': metric['components']['dimension']['correct_geometry_and_value']}), flush=True)
    receipt = {k: {'aggregate': aggregate(v), 'rows': v} if v else None for k, v in results.items()}
    receipt.update(model_sha256=release['model_sha256'], full_training_executed=False,
                   threshold_or_checkpoint_selection_from_twenty=False)
    write(args.output / 'receipt.json', receipt)
    print(json.dumps({k: v['aggregate'] for k, v in receipt.items() if k in ('five', 'twenty') and v}))


if __name__ == '__main__':
    main()
