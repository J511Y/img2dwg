"""Apply predicted shared-axis/dimension equations without CAD target access."""
import copy
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import lsqr


def project(bundle,axis_tolerance_mm=1.,maximum_displacement_mm=None):
    if maximum_displacement_mm is not None and maximum_displacement_mm<=0:raise ValueError('Positive projection trust region required')
    out=copy.deepcopy(bundle); points=np.asarray(out['nodes_mm'],float); rows=[]; rhs=[]
    # Only confidently predicted links are enforced; the model must learn them.
    axis=out.get('axis_links',[]); confidence=out.get('axis_confidence',[]); rejected_axes=0
    for d,links in enumerate(axis):
        for i,j in enumerate(links):
            if i==j or not confidence or confidence[d][i]<.95: continue
            if abs(points[i,d]-points[j,d])>axis_tolerance_mm:
                rejected_axes+=1;continue
            rows.append({i*2+d:1.,j*2+d:-1.}); rhs.append(0.)
    for c in out['components']:
        if c['kind']!='dimension' or len(set(c['nodes'][:2]))<2: continue
        i,j=c['nodes'][:2]; p=c['parameters']
        if p['dimension_kind']==0:
            theta=math.radians(p['angle_cad']); u=np.array([math.cos(theta),-math.sin(theta)])
        else:
            v=points[j]-points[i]; u=v/max(np.linalg.norm(v),1e-9)
        if float((points[j]-points[i])@u)<0: u=-u
        rows.append({i*2:-u[0],i*2+1:-u[1],j*2:u[0],j*2+1:u[1]}); rhs.append(p['value_mm'])
    if rows:
        rr=[]; cc=[]; vv=[]
        for r,values in enumerate(rows):
            for k,v in values.items(): rr.append(r); cc.append(k); vv.append(v)
        matrix=coo_matrix((vv,(rr,cc)),shape=(len(rows),points.size)).tocsr()
        residual=np.asarray(rhs)-matrix@points.ravel()
        delta=lsqr(matrix,residual,atol=1e-11,btol=1e-11,iter_lim=points.size*2)[0]
        displacement=float(np.linalg.norm(delta.reshape(-1,2),axis=1).max())
        if maximum_displacement_mm is not None and displacement>maximum_displacement_mm:
            out['constraint_receipt']={'status':'rejected-displacement','equations':len(rows),
                'max_residual_mm':float(np.max(np.abs(residual))),'maximum_node_displacement_mm':0.,
                'proposed_maximum_displacement_mm':displacement,'maximum_allowed_displacement_mm':maximum_displacement_mm,
                'source_CAD_or_GT_access':False,'axis_tolerance_mm':axis_tolerance_mm,'rejected_axis_proposals':rejected_axes}
            return out
        out['nodes_mm']=(points+delta.reshape(-1,2)).tolist()
        final=np.asarray(rhs)-matrix@np.asarray(out['nodes_mm']).ravel()
        out['constraint_receipt']={'equations':len(rows),'max_residual_mm':float(np.max(np.abs(final))),
                                   'maximum_node_displacement_mm':displacement,
                                   'axis_tolerance_mm':axis_tolerance_mm,'rejected_axis_proposals':rejected_axes,
                                   'source_CAD_or_GT_access':False}
    else: out['constraint_receipt']={'equations':0,'max_residual_mm':None,'source_CAD_or_GT_access':False,
                                     'axis_tolerance_mm':axis_tolerance_mm,'rejected_axis_proposals':rejected_axes}
    return out


def snap_major_lengths(bundle, grid_mm=100., minimum_mm=1000.):
    """Optional factory-length editing, preserving nodes and dimension numbers.

    Avoid snapping absolute node coordinates: that can erase wall thickness.
    Only long wall-face spans and rectangular widths/heights are candidates.
    This remains a reviewable edit, not evidence of dimension-host correctness.
    """
    if grid_mm <= 0 or minimum_mm < grid_mm:
        raise ValueError('Invalid major-length grid')
    out = copy.deepcopy(bundle)
    edits = []
    def rounded(value):
        return math.floor(value / grid_mm + .5) * grid_mm
    for c in out['components']:
        p = c['parameters']
        if c['kind'] == 'rectangular_loop':
            for key in ('width_mm', 'height_mm'):
                value = p[key]
                if value >= minimum_mm:
                    updated = rounded(value)
                    if abs(updated-value) > 1e-9:
                        p[key] = updated
                        edits.append({'component': c['id'], 'parameter': key,
                                      'before_mm': value, 'after_mm': updated})
        elif c['kind'] == 'wall_face_pair':
            for i, pair in enumerate(p['face_extents_mm']):
                span = abs(pair[1]-pair[0])
                if span >= minimum_mm:
                    updated = rounded(span)
                    if abs(updated-span) > 1e-9:
                        centre = sum(pair)/2
                        sign = 1 if pair[1] >= pair[0] else -1
                        p['face_extents_mm'][i] = [centre-sign*updated/2, centre+sign*updated/2]
                        edits.append({'component': c['id'], 'parameter': 'face_span_'+str(i),
                                      'before_mm': span, 'after_mm': updated})
    out['length_edit_receipt'] = {'grid_mm': grid_mm, 'minimum_mm': minimum_mm,
        'edits': edits, 'node_coordinates_changed': False, 'numeric_dimensions_changed': False,
        'wall_thickness_changed': False, 'door_sizes_changed': False,
        'dimension_host_consistency_verified': False, 'source_CAD_or_GT_access': False}
    return out
