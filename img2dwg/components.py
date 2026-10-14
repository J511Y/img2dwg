"""CAD-derived parameter assemblies; reconstruction is GT validation, not inference.

Door leaves and arcs, parallel wall faces and rectangular native polylines are
assembled by factories. Unresolved members stay explicit residuals. Layer WIN
does not establish window semantics (it also contains doors and furniture).
"""
import copy
import math
import numpy as np
from img2dwg.vector import arc_parameters


def to_mm(points, frame):
    return (np.asarray(points, dtype=float) - np.asarray(frame['canvas']) / 2) * frame['scale']


def to_pixel(points, frame):
    return (np.asarray(points) / frame['scale'] + np.asarray(frame['canvas']) / 2).tolist()


def prepare_components(graph, native_layers=None):
    source = graph['components']; used = set(); assemblies = []
    frame = {k: copy.deepcopy(graph[k]) for k in ('schema', 'canvas', 'scale', 'units')}
    layers = native_layers or {}
    def layer(c):
        return layers.get(c.get('source_id'), layers.get(c.get('parent'), 'unknown'))
    def add(kind, params, members):
        used.update(members)
        assemblies.append({'id': f'C{len(assemblies):04d}', 'kind': kind, 'parameters': params,
            'members': members, 'roles': [source[i].get('role', 0) for i in members],
            'semantic_status': 'geometry-assembly-candidate;not-staff-confirmed',
            'native_layers': [layer(source[i]) for i in members]})
    # Native dimensions stay measurement components; they are never line pictures.
    for i, c in enumerate(source):
        if c['kind'] == 'dimension':
            add('dimension', {'anchors_mm': to_mm(c['points'], frame).tolist(),
                'value_mm': c['measurement_mm'], 'dimension_kind': c['dimension_kind'],
                'angle_cad': c['angle_cad']}, [i])
    # Geometry-derived swing opening: radius/hinge/angle + matched leaf, not WIN class.
    for i, c in enumerate(source):
        if i in used or c['kind'] != 'arc':
            continue
        p = to_mm(c['points'], frame); arc = arc_parameters(p)
        if arc is None:
            continue
        center, radius, angles, sweep, extent = arc
        if not 400 <= radius <= 1300 or not 75 <= extent <= 110:
            continue
        match = None
        for j, line in enumerate(source):
            if j in used or line['kind'] != 'segment':
                continue
            a, b, _ = to_mm(line['points'], frame)
            if np.linalg.norm(b - center) < np.linalg.norm(a - center):
                a, b = b, a
            distance = min(np.linalg.norm(b - p[0]), np.linalg.norm(b - p[2]))
            error = np.linalg.norm(a - center) + distance
            if np.linalg.norm(a - center) <= 2 and distance <= 2 and (match is None or error < match[0]):
                match = error, j, a, b
        if match:
            _, j, a, b = match
            leaf_at = 0 if np.linalg.norm(b - p[0]) <= np.linalg.norm(b - p[2]) else 1
            reference_angle = angles[0] if leaf_at == 0 else angles[2]
            add('swing_opening', {'hinge_mm': center.tolist(), 'radius_mm': radius,
                'start_degrees': angles[0], 'extent_degrees': extent, 'sweep': sweep,
                'leaf_hinge_offset_ratio': ((a - center) / radius).tolist(),
                'leaf_length_ratio': float(np.linalg.norm(b - a)) / radius, 'leaf_at': leaf_at,
                'leaf_angle_offset_degrees': math.degrees(math.atan2((b - a)[1], (b - a)[0])) - reference_angle}, [i, j])
    # Native closed four-edge rectangle -> one pose/size component.
    groups = {}
    for i, c in enumerate(source):
        if i not in used and c['kind'] == 'segment' and c.get('parent'):
            groups.setdefault(c['parent'], []).append(i)
    for parent, members in groups.items():
        if len(members) != 4:
            continue
        ends = np.concatenate([to_mm(source[i]['points'][:2], frame) for i in members])
        points = []
        for p in ends:
            if not any(np.linalg.norm(p - q) < 1e-5 for q in points):
                points.append(p)
        if len(points) != 4:
            continue
        points = np.asarray(points); center = points.mean(0)
        order = np.argsort(np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]))
        corners = points[order]; delta = np.roll(corners, -1, axis=0) - corners
        lengths = np.linalg.norm(delta, axis=1)
        if min(lengths) <= 1e-5 or abs(float(delta[0] @ delta[1])) > 1e-9 * lengths[0] * lengths[1]:
            continue
        if max(abs(lengths[0] - lengths[2]), abs(lengths[1] - lengths[3])) > 1e-5:
            continue
        add('rectangular_loop', {'center_mm': center.tolist(), 'width_mm': lengths[0],
            'height_mm': lengths[1], 'angle_degrees': math.degrees(math.atan2(delta[0, 1], delta[0, 0]))}, members)
    # Wall candidate faces share a spine and thickness; individual extents remain exact.
    faces = []
    for i, c in enumerate(source):
        if i in used or c['kind'] != 'segment':
            continue
        if c.get('role') != 2 and '조적' not in layer(c):
            continue
        a, b, _ = to_mm(c['points'], frame); length = np.linalg.norm(b - a)
        if length >= 500:
            faces.append((i, a, b, (b - a) / length, length))
    candidates = []
    for k, first in enumerate(faces):
        for second in faces[k + 1:]:
            i, a, b, u, length = first; j, c, d, v, other = second
            if abs(float(u[0] * v[1] - u[1] * v[0])) > 1e-10:
                continue
            n = np.asarray([-u[1], u[0]]); gap = abs(float((c - a) @ n))
            interval_a = sorted([a @ u, b @ u]); interval_b = sorted([c @ u, d @ u])
            overlap = min(interval_a[1], interval_b[1]) - max(interval_a[0], interval_b[0])
            if 50 <= gap <= 500 and overlap >= 500 and overlap / min(length, other) >= .65:
                candidates.append((gap, i, j, a, b, c, d, u, n))
    candidates.sort(key=lambda x: x[0])
    for gap, i, j, a, b, c, d, u, n in candidates:
        if i in used or j in used:
            continue
        center = (a + b + c + d) / 4
        add('wall_face_pair', {'spine_origin_mm': center.tolist(), 'angle_degrees': math.degrees(math.atan2(u[1], u[0])),
            'thickness_mm': gap, 'face_extents_mm': [[float((a - center) @ u), float((b - center) @ u)],
                                                   [float((c - center) @ u), float((d - center) @ u)]],
            'face_signs': [1 if (a - center) @ n >= 0 else -1,
                           1 if (c - center) @ n >= 0 else -1]}, [i, j])
    # Native CEN guides are graph edges; remaining geometry remains visibly unresolved.
    for i, c in enumerate(source):
        if i in used:
            continue
        if c['kind'] == 'segment' and layer(c) == 'CEN':
            add('centerline', {'endpoints_mm': to_mm(c['points'][:2], frame).tolist()}, [i])
        else:
            # Do not relabel ungrouped strokes as a business component.
            add('unresolved_residual', {'native_kind': c['kind'], 'points_mm': to_mm(c['points'], frame).tolist(),
                'metadata': {k: copy.deepcopy(v) for k, v in c.items() if k not in ('kind', 'points')}}, [i])
    nodes = []; edges = []; lookup = {}
    for assembly in assemblies:
        p = assembly['parameters']; anchors = []
        if assembly['kind'] == 'dimension': anchors = p['anchors_mm'][:2]
        elif assembly['kind'] == 'centerline': anchors = p['endpoints_mm']
        elif assembly['kind'] == 'swing_opening': anchors = [p['hinge_mm']]
        elif assembly['kind'] == 'wall_face_pair':
            angle = math.radians(p['angle_degrees']); direction = np.asarray([math.cos(angle), math.sin(angle)])
            low = min(min(x) for x in p['face_extents_mm']); high = max(max(x) for x in p['face_extents_mm'])
            anchors = [(np.asarray(p['spine_origin_mm']) + t * direction).tolist() for t in (low, high)]
        ids = []
        for point in anchors:
            key = tuple(np.round(point, 3)); node = lookup.get(key)
            if node is None:
                node = len(nodes); nodes.append(point); lookup[key] = node
            ids.append(node)
        if ids:
            assembly['anchor_nodes'] = ids; edges.append({'component': assembly['id'], 'nodes': ids})
    walls = [a for a in assemblies if a['kind'] == 'wall_face_pair']
    for assembly in assemblies:
        if assembly['kind'] != 'swing_opening': continue
        hinge = np.asarray(assembly['parameters']['hinge_mm']); candidates = []
        for wall in walls:
            p = wall['parameters']; angle = math.radians(p['angle_degrees'])
            u = np.asarray([math.cos(angle), math.sin(angle)]); n = np.asarray([-u[1], u[0]])
            delta = hinge - p['spine_origin_mm']; along = float(delta @ u)
            low = min(min(x) for x in p['face_extents_mm']); high = max(max(x) for x in p['face_extents_mm'])
            offset = float(delta @ n)
            if low - 2 <= along <= high + 2 and abs(offset) <= p['thickness_mm'] / 2 + 2:
                candidates.append({'wall': wall['id'], 'along_mm': along, 'offset_mm': offset,
                                   'status': 'geometry-host-candidate;not-confirmed'})
        assembly['host_candidates'] = candidates
    return {'schema': 'img2dwg-component-assemblies/v1', 'frame': frame, 'components': assemblies,
            'nodes_mm': nodes, 'relationships': edges, 'input_source': 'CAD-ground-truth;not-model-prediction',
            'window_semantics_confirmed': False, 'complete_component_catalog': False}


def assemble(bundle):
    frame = bundle['frame']; result = {**copy.deepcopy(frame), 'components': []}
    for assembly in bundle['components']:
        kind = assembly['kind']; p = assembly['parameters']; pieces = []
        if kind == 'dimension':
            pieces.append({'kind': 'dimension', 'points': to_pixel(p['anchors_mm'], frame),
                'measurement_mm': p['value_mm'], 'value_text': str(round(p['value_mm'])),
                'dimension_kind': p['dimension_kind'], 'angle_cad': p['angle_cad']})
        elif kind == 'swing_opening':
            center = np.asarray(p['hinge_mm']); start = p['start_degrees']; extent = p['extent_degrees']
            angles = np.radians(start + np.asarray([0, .5, 1]) * extent * (1 if p['sweep'] else -1))
            curve = center + p['radius_mm'] * np.stack((np.cos(angles), np.sin(angles)), 1)
            a = center + np.asarray(p['leaf_hinge_offset_ratio']) * p['radius_mm']
            reference = start + p['leaf_at'] * extent * (1 if p['sweep'] else -1)
            angle = math.radians(reference + p['leaf_angle_offset_degrees'])
            b = a + p['leaf_length_ratio'] * p['radius_mm'] * np.asarray([math.cos(angle), math.sin(angle)])
            pieces.extend([{'kind': 'arc', 'points': to_pixel(curve, frame)},
                           {'kind': 'segment', 'points': to_pixel([a, b, (a + b) / 2], frame)}])
        elif kind == 'rectangular_loop':
            theta = math.radians(p['angle_degrees']); u = np.asarray([math.cos(theta), math.sin(theta)])
            n = np.asarray([-u[1], u[0]]); c = np.asarray(p['center_mm'])
            corners = np.asarray([c + sx * p['width_mm'] / 2 * u + sy * p['height_mm'] / 2 * n
                                  for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]])
            for a, b in zip(corners, np.roll(corners, -1, axis=0)):
                pieces.append({'kind': 'segment', 'points': to_pixel([a, b, (a + b) / 2], frame)})
        elif kind == 'wall_face_pair':
            theta = math.radians(p['angle_degrees']); u = np.asarray([math.cos(theta), math.sin(theta)])
            n = np.asarray([-u[1], u[0]]); center = np.asarray(p['spine_origin_mm'])
            for extent, sign in zip(p['face_extents_mm'], p['face_signs']):
                offset = sign * p['thickness_mm'] / 2
                a, b = (center + t * u + offset * n for t in extent)
                pieces.append({'kind': 'segment', 'points': to_pixel([a, b, (a + b) / 2], frame)})
        elif kind == 'centerline':
            a, b = np.asarray(p['endpoints_mm'])
            pieces.append({'kind': 'segment', 'points': to_pixel([a, b, (a + b) / 2], frame)})
        else:
            pieces.append({'kind': p['native_kind'], 'points': to_pixel(p['points_mm'], frame), **p['metadata']})
        for j, piece in enumerate(pieces):
            piece.update(role=assembly['roles'][min(j, len(assembly['roles']) - 1)],
                         component_id=assembly['id'], assembly_kind=kind)
            result['components'].append(piece)
    result.update(geometry_source='CAD-parameter-factory;ground-truth-reconstruction-only',
                  numeric_dimensions_verified=False, model_restoration=False,
                  component_assemblies=True, assemblies=copy.deepcopy(bundle['components']))
    return result
