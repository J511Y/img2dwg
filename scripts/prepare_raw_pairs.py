"""Freeze five real-image training pairs and twenty disjoint validation pairs."""
import argparse
import collections
import hashlib
import json
import sys
import tarfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from img2dwg.cad import extract, render
from img2dwg.inference import normalize_image
from img2dwg.vector import exports


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compact(graph):
    """Remove only recorded outer-frame candidates; keep every native dimension."""
    size = graph['canvas'][0]
    kept, removed = [], []
    for c in graph['components']:
        p = np.asarray(c['points']); d = np.abs(p[1] - p[0])
        border = (p[:2] < size * .12).all(0).any() or (p[:2] > size * .88).all(0).any()
        if c['kind'] == 'segment' and max(d) > size * .75 and min(d) < .1 and border:
            removed.append(c)
        else:
            kept.append(c)
    all_points = np.concatenate([np.asarray(c['points']) for c in kept])
    low, high = all_points.min(0), all_points.max(0)
    factor = (size - 48) / max(high - low)
    offset = (size - (high - low) * factor) / 2
    for c in kept:
        c['points'] = ((np.asarray(c['points']) - low) * factor + offset).tolist()
    graph.update(components=kept, scale=graph['scale'] / factor, texts=[])
    graph['preprocessing'] = {'frame_candidates_removed': len(removed),
        'semantic_exclusive_unit_confirmed': False, 'min_length_filter_pixels': 0,
        'output_frame': 'canonical-CAD-uniform-fit;not-input-image-coordinates'}
    return graph


def fingerprint(graph):
    image = render(graph).convert('L').resize((64, 64))
    return np.asarray(image) < 210


def same_family(a, b):
    # Conservative CAD-only grouping check, never image-to-CAD point matching.
    for mirror in (b, np.fliplr(b)):
        for turn in range(4):
            candidate = np.rot90(mirror, turn)
            union = np.logical_or(a, candidate).sum()
            if union and np.logical_and(a, candidate).sum() / union >= .85:
                return True
    return False


def prepare(args):
    args.output.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(x) for x in (args.dataset / 'bundle/records.jsonl').read_text(encoding='utf-8').splitlines()]
    # Sampling is fixed before training or viewing predictions; no performance selection.
    rows.sort(key=lambda r: hashlib.sha256((str(args.seed) + r['sample_id']).encode()).hexdigest())
    train, validation, selection = [], [], []
    groups, source_images, source_cads, fingerprints = set(), set(), set(), []
    for split, count, chosen in [('train', 5, train), ('validation', 20, validation)]:
        for row in rows:
            if row['split'] != split or len(chosen) >= count:
                continue
            if row['group_id'] in groups or row['image_sha256'] in source_images or row['cad_target_sha256'] in source_cads:
                selection.append({'sample_id': row['sample_id'], 'reason': 'duplicate-source-or-group'})
                continue
            source = args.dataset / 'cases' / row['sample_id']
            graph = compact(extract(source / 'before.dxf', row['crop']['bbox'], args.size, min_length_pixels=0))
            pattern = fingerprint(graph)
            if any(same_family(pattern, old) for old in fingerprints):
                selection.append({'sample_id': row['sample_id'], 'reason': 'conservative-CAD-near-family'})
                continue
            folder = args.output / row['sample_id']; folder.mkdir(exist_ok=True)
            image_path = source / row['image_path']
            assert digest(image_path) == row['image_sha256']
            assert digest(source / 'before.dxf') == row['cad_target_sha256']
            with Image.open(image_path) as image:
                image.seek(row.get('primary_frame_index', 0))
                canvas, transform = normalize_image(image, args.size)
                canvas.save(folder / 'input.png')
            graph.update(sample_id=row['sample_id'], group_id=row['group_id'], split=split,
                         source_sha256=row['cad_target_sha256'])
            dims = [c for c in graph['components'] if c['kind'] == 'dimension']
            expected = row['dimension_preservation']['actual_count']
            graph['native_dimension_coverage'] = {'expected': expected, 'supported': len(dims),
                'missing_or_unsupported': expected - len(dims)}
            (folder / 'target.json').write_text(json.dumps(graph, ensure_ascii=False), encoding='utf-8')
            render(graph).save(folder / 'target.png')
            factory = exports(graph, folder / 'factory')
            item = {'sample_id': row['sample_id'], 'split': split, 'group_id': row['group_id'],
                'original_image_sha256': row['image_sha256'], 'source_cad_sha256': row['cad_target_sha256'],
                'input_sha256': digest(folder / 'input.png'), 'target_sha256': digest(folder / 'target.json'),
                'image_transform': transform, 'components': dict(collections.Counter(c['kind'] for c in graph['components'])),
                'native_dimension_coverage': graph['native_dimension_coverage'], 'factory': factory}
            chosen.append(item); groups.add(row['group_id']); source_images.add(row['image_sha256'])
            source_cads.add(row['cad_target_sha256']); fingerprints.append(pattern)
            print(json.dumps({'prepared': row['sample_id'], 'split': split, 'components': item['components'],
                              'dimensions': graph['native_dimension_coverage']}), flush=True)
    assert len(train) == 5 and len(validation) == 20
    index = train + validation
    summary = {'schema': 'img2dwg-real-pairs/v1', 'train': 5, 'validation': 20, 'seed': args.seed,
        'resolution': args.size, 'input_domain': 'original-as-built-raster;EXIF-and-letterbox-only',
        'target_domain': 'native-before-CAD;uniform-canonical-frame', 'selection_exclusions': selection,
        'source_unchanged': True, 'exact_source_group_overlap': 0,
        'near_family_check': 'CAD-render-64px-IoU>=.85 over rotations/reflections;not-perfect-family-proof',
        'complete_semantic_catalog': False,
        'required_dimensions_missing_in_supervision': sum(r['native_dimension_coverage']['missing_or_unsupported'] for r in index),
        'policy': '5 training only;20 validation not used for optimization, threshold or checkpoint selection'}
    (args.output / 'index.json').write_text(json.dumps(index, indent=2), encoding='utf-8')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    with tarfile.open(args.output / 'pairs.tar.gz', 'w:gz') as archive:
        for name in ('index.json', 'summary.json'):
            archive.add(args.output / name, arcname=name)
        for row in index:
            for name in ('input.png', 'target.json'):
                archive.add(args.output / row['sample_id'] / name, arcname=row['sample_id'] + '/' + name)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--size', type=int, default=512)
    parser.add_argument('--seed', type=int, default=20261014)
    prepare(parser.parse_args())
