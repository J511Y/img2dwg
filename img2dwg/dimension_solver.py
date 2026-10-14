"""Project model-predicted dimension constraints onto shared vector endpoints.

Uses predicted coordinates, kinds and numeric values only. No CAD target/OCR
truth lookup. Endpoint clustering is a proposed association, not a confirmed host.
"""
import copy
import math
import numpy as np
from scipy.spatial import cKDTree


def constrain_dimensions(graph, join_mm=2.):
    graph = copy.deepcopy(graph)
    references, points = [], []
    for i, c in enumerate(graph['components']):
        if c['kind'] not in ('segment', 'dimension'):
            continue
        for j in (0, 1):
            references.append((i, j)); points.append(np.asarray(c['points'][j]) * graph['scale'])
    if not points:
        graph['dimension_solver'] = {'status': 'no-endpoints', 'target_access': False}
        return graph
    points = np.asarray(points); root = list(range(len(points)))
    def find(i):
        while root[i] != i:
            root[i] = root[root[i]]; i = root[i]
        return i
    for i, j in sorted(cKDTree(points).query_pairs(join_mm)):
        a, b = find(i), find(j)
        if a != b:
            root[max(a, b)] = min(a, b)
    groups = {}; node_for_ref = {}
    for i, ref in enumerate(references):
        groups.setdefault(find(i), []).append(i)
    values = []
    for group in groups.values():
        node = len(values); values.append(points[group].mean(0))
        for entry in group:
            node_for_ref[references[entry]] = node
    original = np.asarray(values); solved = original.copy(); constraints = []; invalid = 0
    for i, c in enumerate(graph['components']):
        if c['kind'] != 'dimension':
            continue
        value = float(c.get('predicted_value_mm', 0))
        if not value > 0:
            invalid += 1; continue
        a, b = node_for_ref[i, 0], node_for_ref[i, 1]
        if a == b:
            invalid += 1; continue
        angle = float(c.get('angle_cad', 0))
        # Quantize only a near-orthogonal predicted dimension measurement axis.
        nearest = round(angle / 90) * 90
        if abs(angle - nearest) <= 1:
            angle = nearest; c['angle_cad'] = angle
        direction = np.asarray([math.cos(math.radians(angle)), -math.sin(math.radians(angle))])
        if c.get('dimension_kind', 1) == 1:
            direction = original[b] - original[a]
            direction /= max(np.linalg.norm(direction), 1e-8)
        sign = 1 if (original[b] - original[a]) @ direction >= 0 else -1
        constraints.append((a, b, direction, sign * value))
    residual = 0.
    if constraints:
        matrix = np.zeros((len(constraints), len(values) * 2)); target = np.zeros(len(constraints))
        for i, (a, b, direction, value) in enumerate(constraints):
            matrix[i, a * 2:a * 2 + 2] = -direction
            matrix[i, b * 2:b * 2 + 2] = direction; target[i] = value
        # Minimum displacement subject to predicted dimension equalities.
        delta = matrix @ original.ravel() - target
        multipliers = np.linalg.lstsq(matrix @ matrix.T, delta, rcond=1e-10)[0]
        solved = (original.ravel() - matrix.T @ multipliers).reshape(-1, 2)
        residual = float(np.abs(matrix @ solved.ravel() - target).max(initial=0))
    displacement = np.linalg.norm(solved - original, axis=1)
    for i, ref in enumerate(references):
        component, endpoint = ref
        graph['components'][component]['points'][endpoint] = (solved[node_for_ref[ref]] / graph['scale']).tolist()
    for c in graph['components']:
        if c['kind'] == 'segment':
            c['points'][2] = ((np.asarray(c['points'][0]) + c['points'][1]) / 2).tolist()
    graph['geometry_source'] += '+predicted-dimension-constraint-projection'
    graph['dimension_solver'] = {'status': 'projected' if residual <= 1 else 'conflicting-predicted-constraints',
        'constraints': len(constraints), 'invalid_constraints': invalid, 'maximum_residual_mm': residual,
        'maximum_displacement_mm': float(displacement.max(initial=0)), 'join_mm': join_mm,
        'association': 'predicted-endpoint-proximity;not-confirmed-host', 'target_access': False}
    return graph
