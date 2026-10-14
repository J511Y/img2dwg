"""Frozen physical-geometry and native-dimension checks; never shape-only success."""
import math
import numpy as np
from scipy.optimize import linear_sum_assignment
from img2dwg.vector import KINDS

PROTOCOL = {'geometry_tolerance_mm': 10., 'dimension_tolerance_mm': 1.,
            'required_dimension_coverage': 1., 'minimum_structure_f1': .90,
            'confidence_threshold': .5, 'alignment': 'fixed-centered-canonical-frame;no-fit-to-target',
            'pair_matching': 'unordered-Hungarian;maximum-endpoint-and-arc-midpoint-or-dimension-label-distance'}


def physical(c, graph):
    return (np.asarray(c['points'], dtype=float) - np.asarray(graph['canvas']) / 2) * graph['scale']


def measurement(c, graph):
    a, b, _ = physical(c, graph)
    if c.get('dimension_kind', 1) == 0:
        angle = math.radians(c['angle_cad'])
        return abs(float((b - a) @ np.asarray([math.cos(angle), -math.sin(angle)])))
    return float(np.linalg.norm(b - a))


def evaluate_case(predicted, target, factory=None):
    counts = {}; details = []; associations = {}
    for kind in KINDS:
        p = [c for c in predicted['components'] if c['kind'] == kind]
        t = [c for c in target['components'] if c['kind'] == kind]
        a = np.asarray([physical(c, predicted) for c in p]).reshape(-1, 3, 2)
        b = np.asarray([physical(c, target) for c in t]).reshape(-1, 3, 2)
        matched = []; full_rows = []
        if len(a) and len(b):
            end = [0, 2] if kind == 'arc' else [0, 1]
            direct = np.linalg.norm(a[:, None, end] - b[None, :, end], axis=-1).max(-1)
            reverse = np.linalg.norm(a[:, None, end] - b[None, :, end[::-1]], axis=-1).max(-1)
            distances = np.minimum(direct, reverse)
            if kind in ('dimension', 'arc'):
                mid = 1 if kind == 'arc' else 2
                distances = np.maximum(distances, np.linalg.norm(a[:, None, mid] - b[None, :, mid], axis=-1))
            rows, cols = linear_sum_assignment(distances)
            for i, j in zip(rows.tolist(), cols.tolist()):
                row = {'predicted_index': i, 'target_index': j, 'max_point_error_mm': float(distances[i, j])}
                if kind == 'dimension':
                    value = float(t[j]['measurement_mm'])
                    row.update(target_value_mm=value, predicted_value_mm=float(p[i]['predicted_value_mm']),
                               numeric_error_mm=abs(float(p[i]['predicted_value_mm']) - value),
                               geometry_error_mm=abs(measurement(p[i], predicted) - value),
                               label_geometry_residual_mm=abs(measurement(p[i], predicted) - float(p[i]['predicted_value_mm'])))
                full_rows.append(row)
                if distances[i, j] <= PROTOCOL['geometry_tolerance_mm']:
                    matched.append(row)
        precision = len(matched) / len(p) if p else 0.
        recall = len(matched) / len(t) if t else 0.
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.
        counts[kind] = {'predicted': len(p), 'target': len(t), 'matched': len(matched), 'precision': precision, 'recall': recall, 'f1': f1}
        if kind == 'dimension':
            valid = [r for r in matched if r['numeric_error_mm'] <= 1 and r['geometry_error_mm'] <= 1
                     and r['label_geometry_residual_mm'] <= 1]
            counts[kind].update(correct_geometry_and_value=len(valid), missing_or_incorrect=len(t) - len(valid),
                extra_predicted=max(0, len(p) - len(t)),
                maximum_numeric_error_mm=max((r['numeric_error_mm'] for r in full_rows), default=None),
                maximum_geometry_error_mm=max((r['geometry_error_mm'] for r in full_rows), default=None))
            details = full_rows
    structure = [counts[k] for k in ('segment', 'arc')]
    p, t, m = (sum(x[key] for x in structure) for key in ('predicted', 'target', 'matched'))
    f1 = 2 * m / (p + t) if p + t else 0.
    target_coverage = target.get('native_dimension_coverage', {}).get('missing_or_unsupported', 0)
    native_instances = counts['symbol']
    passed = (f1 >= .90 and counts['dimension']['missing_or_incorrect'] == 0
              and counts['dimension']['extra_predicted'] == 0 and target_coverage == 0
              and native_instances['matched'] == native_instances['target']
              and factory is not None and factory['audit_errors'] == 0)
    return {'passed': bool(passed), 'structure_f1': f1, 'components': counts,
            'dimension_details': details, 'native_dimension_supervision_missing': target_coverage,
            'factory': factory, 'semantic_wall_door_host_validation_complete': False,
            'complete_DWG_product_passed': False}


def aggregate(rows):
    dimensions = [r['components']['dimension'] for r in rows]
    structure = [r['components'][k] for r in rows for k in ('segment', 'arc')]
    p, t, m = (sum(x[key] for x in structure) for key in ('predicted', 'target', 'matched'))
    return {'cases': len(rows), 'passed_cases': sum(r['passed'] for r in rows),
            'structure_f1': 2 * m / (p + t) if p + t else 0.,
            'required_dimensions': sum(r['target'] for r in dimensions),
            'dimensions_correct_geometry_and_value': sum(r['correct_geometry_and_value'] for r in dimensions),
            'dimensions_missing_or_incorrect': sum(r['missing_or_incorrect'] for r in dimensions)}
