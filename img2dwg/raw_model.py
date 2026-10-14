"""Real raster -> canonical typed component parameters, independent of pixel frame.

Canonical geometric order supplies sequence supervision; no raster stroke/handle
matching and no target retrieval are used in forward or decode. Evaluation is set
based. Native dimension values and active-instance membership have separate heads.
"""
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from img2dwg.vector import KINDS, ROLES, arc_parameters


def ordered(graph):
    return sorted(graph['components'], key=lambda c: (KINDS.index(c['kind']), tuple(np.asarray(c['points']).ravel())))


def encode_target(graph, queries, parent_classes):
    components = ordered(graph)
    if len(components) > queries:
        raise ValueError('Training capacity cannot silently drop components')
    size = graph['canvas'][0]
    kind = np.full(queries, len(KINDS), np.int64)
    geometry = np.zeros((queries, 6), np.float32)
    roles = np.full(queries, -1, np.int64)
    digits = np.full((queries, 5), -1, np.int64)
    parent = np.zeros(queries, np.int64)
    angle = np.zeros((queries, 2), np.float32)
    dim_kind = np.full(queries, -1, np.int64)
    measurement = np.zeros(queries, np.float32)
    symbols = [c for c in components if c['kind'] == 'symbol']
    parents = {c['parent']: i + 1 for i, c in enumerate(symbols) if c.get('parent')}
    for i, c in enumerate(components):
        kind[i] = KINDS.index(c['kind']); roles[i] = c.get('role', 0)
        p = np.asarray(c['points']) / size
        if c['kind'] == 'arc':
            center, radius, angles, sweep, extent = arc_parameters(p)
            # A canonical positive radius replaces unstable three-point regression.
            start = angles[0] if sweep else angles[2]
            geometry[i] = [*center, radius, math.sin(math.radians(start)), math.cos(math.radians(start)), extent / 360]
        else:
            geometry[i] = p.ravel()
        if c['kind'] == 'dimension':
            value = int(round(c['measurement_mm']))
            if not 0 <= value <= 99999:
                raise ValueError('Unsupported dimension value; cannot silently truncate')
            digits[i] = [int(x) for x in f'{value:05d}']
            angle[i] = [math.sin(math.radians(c['angle_cad'])), math.cos(math.radians(c['angle_cad']))]
            dim_kind[i] = c['dimension_kind']
            measurement[i] = c['measurement_mm']
        parent[i] = parents.get(c.get('parent'), 0)
    if parent.max(initial=0) >= parent_classes:
        raise ValueError('Instance relationship capacity exceeded')
    # Native identical endpoints supervise shared-node consistency, not semantics.
    buckets = {}
    for i, c in enumerate(components):
        if c['kind'] == 'arc' or c['kind'] == 'symbol':
            continue
        for j in (0, 1):
            key = tuple(np.round(np.asarray(c['points'][j]) * graph['scale'], 2))
            buckets.setdefault(key, []).append(i * 2 + j)
    pairs = [(entries[0], other) for entries in buckets.values() for other in entries[1:]]
    values = {'kind': kind, 'geometry': geometry, 'role': roles, 'digits': digits,
              'parent': parent, 'angle': angle, 'dim_kind': dim_kind,
              'relations': np.asarray(pairs, np.int64).reshape(-1, 2), 'measurement': measurement}
    result = {k: torch.from_numpy(v) for k, v in values.items()}
    result['log_scale'] = torch.tensor(math.log(graph['scale']), dtype=torch.float32)
    return result


class CanonicalDecoder(nn.Module):
    def __init__(self, queries, parents=64, hidden=192, input_dim=768):
        super().__init__()
        self.queries = queries; self.parents = parents
        self.project = nn.Linear(input_dim, hidden)
        self.query = nn.Embedding(queries, hidden)
        self.condition = nn.Sequential(nn.Linear(input_dim * 2, hidden * 2), nn.GELU(), nn.Linear(hidden * 2, hidden * 2))
        self.attention = nn.ModuleList([nn.MultiheadAttention(hidden, 6, dropout=0, batch_first=True) for _ in range(2)])
        self.norm = nn.ModuleList([nn.LayerNorm(hidden) for _ in range(2)])
        self.mlp = nn.Sequential(nn.Linear(hidden, hidden * 2), nn.GELU(), nn.Linear(hidden * 2, hidden), nn.GELU())
        self.kind = nn.Linear(hidden, 5); self.geometry = nn.Linear(hidden, 6)
        self.arc = nn.Linear(hidden, 6); self.role = nn.Linear(hidden, len(ROLES))
        self.digits = nn.Linear(hidden, 50); self.parent = nn.Linear(hidden, parents)
        self.angle = nn.Linear(hidden, 2); self.dim_kind = nn.Linear(hidden, 2)
        self.scale = nn.Sequential(nn.Linear(input_dim * 2, hidden), nn.GELU(), nn.Linear(hidden, 1))
        self.scale[-1].bias.data.fill_(3.)

    def forward(self, features):
        pooled = torch.cat((features.mean(1), features.amax(1)), -1)
        gain, shift = self.condition(pooled).chunk(2, -1)
        query = self.query.weight[None] * (1 + gain[:, None].tanh()) + shift[:, None]
        memory = self.project(features)
        for attn, norm in zip(self.attention, self.norm):
            query = norm(query + attn(query, memory, memory, need_weights=False)[0])
        query = query + self.mlp(query)
        arc = self.arc(query)
        stable_arc = torch.cat((arc[..., :2].sigmoid() * 3 - 1, arc[..., 2:3].sigmoid() * 1.5 + 1e-5,
                                arc[..., 3:5].tanh(), arc[..., 5:].sigmoid()), -1)
        return {'kind': self.kind(query), 'geometry': self.geometry(query).sigmoid(), 'arc': stable_arc,
                'role': self.role(query), 'digits': self.digits(query).reshape(*query.shape[:2], 5, 10),
                'parent': self.parent(query), 'angle': self.angle(query), 'dim_kind': self.dim_kind(query),
                'log_scale': self.scale(pooled).squeeze(-1)}


def raw_loss(pred, targets, physical_weight=0):
    total = pred['kind'].sum() * 0; details = {}
    for batch, target in enumerate(targets):
        k = target['kind']; active = k < 4; arcs = k == 1; dims = k == 2
        weights = pred['kind'].new_tensor([1., 2., 4., 2., .2])
        classification = F.cross_entropy(pred['kind'][batch], k, weight=weights)
        coordinate = F.smooth_l1_loss(pred['geometry'][batch, active & ~arcs], target['geometry'][active & ~arcs], beta=.005)
        curve = F.smooth_l1_loss(pred['arc'][batch, arcs], target['geometry'][arcs], beta=.005) if arcs.any() else classification * 0
        role = F.cross_entropy(pred['role'][batch, active], target['role'][active])
        parents = F.cross_entropy(pred['parent'][batch, active], target['parent'][active])
        digits = F.cross_entropy(pred['digits'][batch, dims].reshape(-1, 10), target['digits'][dims].reshape(-1)) if dims.any() else classification * 0
        angle = F.mse_loss(pred['angle'][batch, dims], target['angle'][dims]) if dims.any() else classification * 0
        dimension_kind = F.cross_entropy(pred['dim_kind'][batch, dims], target['dim_kind'][dims]) if dims.any() else classification * 0
        scale = F.mse_loss(pred['log_scale'][batch], target['log_scale'])
        relations = target['relations']; points = pred['geometry'][batch, :, :4].reshape(-1, 2)
        shared = F.mse_loss(points[relations[:, 0]], points[relations[:, 1]]) if len(relations) else classification * 0
        part = classification + 100 * coordinate + 10 * curve + .25 * role + .25 * parents + digits + angle + .5 * dimension_kind + scale + 20 * shared
        if physical_weight:
            p = (pred['geometry'][batch].reshape(-1, 3, 2) - .5) * 512 * pred['log_scale'][batch].exp()
            truth = (target['geometry'].reshape(-1, 3, 2) - .5) * 512 * target['log_scale'].exp()
            physical = F.smooth_l1_loss(p[active & ~arcs] / 10000, truth[active & ~arcs] / 10000, beta=1e-4)
            delta = p[dims, 1] - p[dims, 0]
            direction = torch.stack((target['angle'][dims, 1], -target['angle'][dims, 0]), -1)
            length = torch.where(target['dim_kind'][dims] == 0, (delta * direction).sum(-1).abs(), delta.norm(dim=-1))
            measured = F.smooth_l1_loss(length / 10000, target['measurement'][dims] / 10000, beta=1e-4)
            part = part + physical_weight * (physical + measured)
            if arcs.any():
                def path(parameters, scale):
                    start = torch.atan2(parameters[:, 3], parameters[:, 4])
                    angles = start[:, None] + parameters[:, 5:6] * (2 * math.pi) * parameters.new_tensor([0., .5, 1.])[None]
                    points = parameters[:, None, :2] + parameters[:, None, 2:3] * torch.stack((angles.cos(), angles.sin()), -1)
                    return (points - .5) * 512 * scale.exp()
                arc_physical = F.smooth_l1_loss(path(pred['arc'][batch, arcs], pred['log_scale'][batch]) / 10000,
                    path(target['geometry'][arcs], target['log_scale']) / 10000, beta=1e-4)
                part = part + physical_weight * arc_physical
                details['curve_physical'] = details.get('curve_physical', 0) + float(arc_physical.detach()) / len(targets)
            details['physical'] = details.get('physical', 0) + float(physical.detach()) / len(targets)
            details['dimension_length'] = details.get('dimension_length', 0) + float(measured.detach()) / len(targets)
        total = total + part / len(targets)
        for name, value in [('kind', classification), ('coordinate', coordinate), ('arc', curve), ('digits', digits), ('scale', scale), ('shared', shared)]:
            details[name] = details.get(name, 0) + float(value.detach()) / len(targets)
    return total, details


def decode_raw(pred, size, threshold=.5):
    probability = pred['kind'][0].softmax(-1).detach().cpu().numpy()
    geometry = pred['geometry'][0].detach().cpu().numpy()
    curves = pred['arc'][0].detach().cpu().numpy()
    roles = pred['role'][0].argmax(-1).cpu().tolist()
    parents = pred['parent'][0].argmax(-1).cpu().tolist()
    digits = pred['digits'][0].argmax(-1).cpu().numpy()
    angles = pred['angle'][0].detach().cpu().numpy()
    dim_kind = pred['dim_kind'][0].argmax(-1).cpu().tolist()
    scale = float(pred['log_scale'][0].detach().clamp(-4, 8).exp())
    components = []; rejected = []
    for i, probability_i in enumerate(probability):
        kind = int(probability_i.argmax())
        if kind == 4 or probability_i[kind] < threshold:
            continue
        if kind == 1:
            center = curves[i, :2] * size; radius = float(curves[i, 2]) * size
            start = math.atan2(curves[i, 3], curves[i, 4]); span = float(curves[i, 5]) * 2 * math.pi
            angles_arc = start + np.asarray([0, span / 2, span])
            points = center + radius * np.stack((np.cos(angles_arc), np.sin(angles_arc)), 1)
            if not np.isfinite(points).all() or (points < -size * .1).any() or (points > size * 1.1).any():
                rejected.append({'query': i, 'reason': 'curve-path-extents'}); continue
        else:
            points = geometry[i].reshape(3, 2) * size
        c = {'kind': KINDS[kind], 'points': points.tolist(), 'role': roles[i], 'confidence': float(probability_i[kind]),
             'query_index': i, 'semantic_status': 'unresolved-or-layer-role-candidate', 'source': 'trained-raw-canonical-decoder'}
        if parents[i]:
            c['parent'] = f'predicted-instance-{parents[i]}'
        if kind == 2:
            value = int(digits[i] @ np.asarray([10000, 1000, 100, 10, 1]))
            c.update(value_text=str(value), predicted_value_mm=value, measurement_mm=value,
                     measurement_status='model-predicted;not-verified', dimension_kind=dim_kind[i],
                     angle_cad=math.degrees(math.atan2(angles[i, 0], angles[i, 1])) % 180)
        components.append(c)
    return {'schema': 'img2dwg-vector/v1', 'canvas': [size, size], 'scale': scale, 'units': 'mm',
            'components': components, 'geometry_source': 'trained-raw-canonical-component-decoder',
            'scale_authority': 'model-regression;not-confirmed', 'rejected_components': rejected,
            'numeric_dimensions_verified': False, 'review_required': True,
            'exclusive_unit_scope': 'before-panel;semantic-exclusive-boundary-unverified',
            'relationship_status': 'learned-instance-membership-and-shared-point-supervision;not-validated'}
