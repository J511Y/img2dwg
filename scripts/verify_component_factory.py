"""Validate parameter assemblies on five CAD targets; never call this ML quality."""
import collections
import json
import sys
from pathlib import Path
import ezdxf
import numpy as np
from scipy.optimize import linear_sum_assignment
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from img2dwg.components import prepare_components, assemble, to_mm
from img2dwg.cad import extract
from img2dwg.vector import KINDS, exports, svg


def verify(root, dataset):
    rows = json.loads((root / 'data/index.json').read_text())[:5]
    results = []
    for row in rows:
        key = row['sample_id']; out = root / 'component-factory' / key; out.mkdir(parents=True, exist_ok=True)
        original = json.loads((root / 'data' / key / 'target.json').read_text())
        native = ezdxf.readfile(dataset / 'cases' / key / 'before.dxf')
        layers = {e.dxf.handle: e.dxf.layer for e in native.modelspace() if e.dxf.hasattr('handle')}
        bundle = prepare_components(original, layers); rebuilt = assemble(bundle)
        (out / 'assemblies.json').write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
        factory = exports(rebuilt, out)
        max_error = 0.; counts = {}
        for kind in KINDS:
            a = [c for c in original['components'] if c['kind'] == kind]
            b = [c for c in rebuilt['components'] if c['kind'] == kind]
            assert len(a) == len(b), (key, kind, len(a), len(b))
            if not a:
                continue
            aa = np.asarray([to_mm(c['points'], original) for c in a]); bb = np.asarray([to_mm(c['points'], rebuilt) for c in b])
            inds = [0, 2] if kind == 'arc' else [0, 1]
            direct = np.linalg.norm(aa[:, None, inds] - bb[None, :, inds], axis=-1).max(-1)
            reverse = np.linalg.norm(aa[:, None, inds] - bb[None, :, inds[::-1]], axis=-1).max(-1)
            distances = np.minimum(direct, reverse)
            if kind == 'arc': distances = np.maximum(distances, np.linalg.norm(aa[:, None, 1] - bb[None, :, 1], axis=-1))
            rr, cc = linear_sum_assignment(distances)
            error = float(distances[rr, cc].max(initial=0)); max_error = max(max_error, error)
            counts[kind] = {'count': len(a), 'max_error_mm': error}
        assert max_error < .001, (key, max_error)
        assert factory['dimension_count'] == row['native_dimension_coverage']['expected']
        assert factory['dimension_max_error_mm'] < .001
        # Reopen real BLOCK/INSERT and compare decomposed world geometry, not JSON only.
        width,height=rebuilt['canvas']; scale=rebuilt['scale']
        reopened=extract(out/'prediction.dxf',[0,0,width*scale,height*scale],width+48,min_length_pixels=0)
        reopen_max=0.
        for kind in ('segment','arc','dimension'):
            a=[c for c in original['components'] if c['kind']==kind]
            b=[c for c in reopened['components'] if c['kind']==kind]
            assert len(a)==len(b),(key,'reopened',kind,len(a),len(b))
            if not a: continue
            aa=np.asarray([to_mm(c['points'],original) for c in a]); bb=np.asarray([to_mm(c['points'],reopened) for c in b])
            inds=[0,2] if kind=='arc' else [0,1]
            direct=np.linalg.norm(aa[:,None,inds]-bb[None,:,inds],axis=-1).max(-1)
            reverse=np.linalg.norm(aa[:,None,inds]-bb[None,:,inds[::-1]],axis=-1).max(-1)
            distances=np.minimum(direct,reverse)
            if kind=='arc': distances=np.maximum(distances,np.linalg.norm(aa[:,None,1]-bb[None,:,1],axis=-1))
            rr,cc=linear_sum_assignment(distances); reopen_max=max(reopen_max,float(distances[rr,cc].max(initial=0)))
        assert reopen_max<.001,(key,'reopened geometry',reopen_max)
        distribution = dict(collections.Counter(c['kind'] for c in bundle['components']))
        grouped = sum(len(c['members']) for c in bundle['components'] if c['kind'] != 'unresolved_residual')
        result = {'sample_id': key, 'status': 'passed-GT-parameter-reconstruction-only',
            'assemblies': distribution, 'original_primitives': len(original['components']),
            'grouped_members': grouped, 'unresolved_residual_members': len(original['components']) - grouped,
            'max_geometry_error_mm': max_error, 'reopened_block_world_geometry_max_error_mm':reopen_max,
            'factory': factory, 'counts': counts,
            'relationships': len(bundle['relationships']), 'model_inference': False}
        results.append(result); print(json.dumps(result), flush=True)
    receipt = {'status': 'five-GT-factories-passed;not-model-training-or-inference', 'cases': results,
               'input_model_not_used': True, 'native_window_layer_is_not_window_label': True,
               'complete_component_catalog': False}
    (root / 'component-factory/receipt.json').write_text(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True); p.add_argument('--dataset', type=Path, required=True)
    args = p.parse_args(); verify(args.root, args.dataset)
