"""Shared-node component IR. Native groups remain geometric, not wall labels.

The compiler reads node references as the sole authority for positions. Small
native paths retain membership; no whole-plan CAD lookup is used at inference.
"""
import copy
import math
import hashlib
import json
import numpy as np
from img2dwg.components import prepare_components, assemble, to_mm, to_pixel
from img2dwg.vector import arc_parameters

TYPES = ('dimension', 'swing_opening', 'wall_face_pair', 'rectangular_loop',
         'centerline', 'native_path', 'circular_arc', 'unresolved_edge', 'text', 'symbol', 'native_symbol')
MAX_REFS = 12
UNIT = 10000.
PARAMS = 16


def prepare(graph, layers=None):
    old = prepare_components(graph, layers)
    source = graph['components']; result = []
    residual = {a['members'][0]: a for a in old['components'] if a['kind'] == 'unresolved_residual'}
    consumed = set()
    # Preserve native connected paths up to twelve vertices. This does not turn
    # a native polyline into a confirmed window, fixture, or room label.
    groups = {}
    for i in residual:
        c = source[i]
        if c['kind'] == 'segment' and c.get('parent'):
            groups.setdefault(c['parent'], []).append(i)
    for parent, members in groups.items():
        if not 2 <= len(members) <= MAX_REFS:
            continue
        edges = [to_mm(source[i]['points'][:2], old['frame']) for i in members]
        vertices = []; links = []
        for pair in edges:
            ids = []
            for p in pair:
                hit = next((j for j, q in enumerate(vertices) if np.linalg.norm(p-q) < .001), None)
                if hit is None: hit = len(vertices); vertices.append(p)
                ids.append(hit)
            links.append(ids)
        if len(vertices) > MAX_REFS: continue
        degree = np.bincount(np.asarray(links).ravel(), minlength=len(vertices))
        if (degree > 2).any(): continue
        start = int(np.flatnonzero(degree == 1)[0]) if (degree == 1).any() else 0
        order = [start]; visited = set()
        while len(visited) < len(links):
            hit = next(((j, b if a == order[-1] else a) for j, (a,b) in enumerate(links)
                        if j not in visited and order[-1] in (a,b)), None)
            if hit is None: break
            j, nxt = hit; visited.add(j); order.append(nxt)
        if len(visited) != len(links): continue
        closed = order[-1] == order[0]
        if closed: order.pop()
        result.append({'kind':'native_path', 'positions_mm':np.asarray(vertices)[order].tolist(),
                       'parameters':{'closed':closed}, 'members':members,
                       'roles':[source[i].get('role',0) for i in members],
                       'native_parent':parent, 'semantic_status':'native-path;business-semantics-unknown'})
        consumed.update(members)
    for a in old['components']:
        kind = a['kind']; p = copy.deepcopy(a['parameters']); members = a['members']
        if kind == 'unresolved_residual' and members[0] in consumed: continue
        positions = []
        if kind == 'dimension': positions = p.pop('anchors_mm')
        elif kind == 'swing_opening': positions = [p.pop('hinge_mm')]
        elif kind == 'wall_face_pair': positions = [p.pop('spine_origin_mm')]
        elif kind == 'rectangular_loop': positions = [p.pop('center_mm')]
        elif kind == 'centerline': positions = p.pop('endpoints_mm')
        elif kind == 'unresolved_residual':
            native = p['native_kind']; points = p['points_mm']
            if native == 'arc':
                arc=arc_parameters(points)
                if arc is None:
                    # Preserve the unresolved witness rather than fabricate a
                    # circle. Original target ARC remains in quality metrics.
                    kind='unresolved_edge';positions=[points[0],points[2]];p={'unsupported_degenerate_native_arc':True}
                else:
                    center, radius, angles, sweep, extent = arc
                    kind = 'circular_arc'; positions = [center.tolist()]
                    p = {'radius_mm':radius, 'start_degrees':angles[0], 'extent_degrees':extent, 'sweep':sweep}
            elif native == 'segment':
                kind = 'unresolved_edge'; positions = points[:2]; p = {}
            else:
                kind = 'symbol'; positions = points[:2]; p = {}
        result.append({**a, 'kind':kind, 'parameters':p, 'positions_mm':positions})
    for position, text in graph.get('texts', []):
        result.append({'kind':'text', 'positions_mm':to_mm([position],old['frame']).tolist(),
                       'parameters':{'text':text, 'height_mm':graph['scale']*9},
                       'members':[], 'roles':[0], 'semantic_status':'native-text;content-preserved'})
    nodes = []; lookup = {}; components = []
    for a in result:
        refs = []
        for point in a.pop('positions_mm'):
            key = tuple(np.round(point,3))
            if key not in lookup: lookup[key] = len(nodes); nodes.append(point)
            refs.append(lookup[key])
        a.update(id=f'C{len(components):04d}', nodes=refs)
        components.append(a)
    # Exact common x/y coordinates connect dimension witness points to faces
    # even when their y/x coordinates lie outside the building outline.
    axes = []
    for axis in (0,1):
        buckets = {}
        for i,p in enumerate(nodes): buckets.setdefault(round(p[axis],3),[]).append(i)
        axes.append([indices for indices in buckets.values() if len(indices)>1])
    walls = [i for i,c in enumerate(components) if c['kind']=='wall_face_pair']
    for a in components:
        a['host'] = -1; a['host_status'] = 'unknown'
        if a['kind']!='swing_opening': continue
        hinge=np.asarray(nodes[a['nodes'][0]]); hosts=[]
        for i in walls:
            w=components[i]; p=w['parameters']; origin=np.asarray(nodes[w['nodes'][0]])
            angle=math.radians(p['angle_degrees']); u=np.array([math.cos(angle),math.sin(angle)])
            n=np.array([-u[1],u[0]]); delta=hinge-origin; along=float(delta@u)
            lo=min(min(e) for e in p['face_extents_mm']); hi=max(max(e) for e in p['face_extents_mm'])
            if lo-2<=along<=hi+2 and abs(float(delta@n))<=p['thickness_mm']/2+2: hosts.append(i)
        if len(hosts)==1: a.update(host=hosts[0],host_status='unique-geometric-candidate;not-staff-confirmed')
    return {'schema':'img2dwg-shared-component/v2', 'frame':old['frame'], 'nodes_mm':nodes,
            'components':components,'axis_groups':axes, 'complete_business_semantics':False,
            'source':'CAD-supervision;not-image-inference', 'native_dimension_coverage':graph.get('native_dimension_coverage',{})}


def compile_graph(bundle,strict=True):
    """Positions exclusively resolve from predicted/GT shared nodes."""
    frame=bundle['frame']; nodes=np.asarray(bundle['nodes_mm']); graph={**copy.deepcopy(frame),'components':[],'texts':[],'assemblies':[],'unsupported_components':[]}
    for index,a in enumerate(bundle['components']):
        refs=a['nodes']
        if not refs or max(refs)>=len(nodes) or min(refs)<0: raise ValueError('Invalid shared-node reference')
        positions=nodes[refs]; kind=a['kind']; p=copy.deepcopy(a['parameters']); pieces=[]
        if kind in ('dimension','swing_opening','wall_face_pair','rectangular_loop','centerline'):
            key={'dimension':'anchors_mm','swing_opening':'hinge_mm','wall_face_pair':'spine_origin_mm',
                 'rectangular_loop':'center_mm','centerline':'endpoints_mm'}[kind]
            p[key]=positions.tolist() if kind in ('dimension','centerline') else positions[0].tolist()
            legacy={**a,'parameters':p}
            rebuilt=assemble({'frame':frame,'components':[legacy]})
            pieces=rebuilt['components']; graph['assemblies'].append(legacy)
            if kind=='dimension':
                pieces[0]['predicted_value_mm']=p['value_mm']
        elif kind=='native_path':
            pairs=list(zip(positions[:-1],positions[1:]))
            if p['closed']: pairs.append((positions[-1],positions[0]))
            for start,end in pairs: pieces.append({'kind':'segment','points':to_pixel([start,end,(start+end)/2],frame)})
            graph['assemblies'].append({**a,'parameters':{'origin_mm':positions[0].tolist(),'size_mm':1.}})
        elif kind=='circular_arc':
            angles=np.radians(p['start_degrees']+np.array([0,.5,1])*p['extent_degrees']*(1 if p['sweep'] else -1))
            points=positions[0]+p['radius_mm']*np.stack([np.cos(angles),np.sin(angles)],1)
            pieces=[{'kind':'arc','points':to_pixel(points,frame)}]
        elif kind=='native_symbol':
            template=bundle.get('templates',{}).get(p['template_id'])
            if template is None:
                if strict:raise ValueError('Unknown native component prototype')
                graph['unsupported_components'].append({'component_id':a['id'],'reason':'unknown-native-prototype','nodes':refs})
                continue
            for child in template:
                points=positions[0]+np.asarray(child['points'])*p['size_mm']
                pieces.append({'kind':child['kind'],'points':to_pixel(points,frame),'role':child['role']})
            graph['assemblies'].append({**a,'parameters':{'origin_mm':positions[0].tolist(),'size_mm':p['size_mm']}})
        elif kind in ('unresolved_edge','symbol'):
            start,end=positions[:2]
            pieces=[{'kind':'segment' if kind=='unresolved_edge' else 'symbol',
                     'points':to_pixel([start,end,(start+end)/2],frame)}]
        elif kind=='text':
            graph['texts'].append((to_pixel(positions,frame)[0],p['text']))
        else: raise ValueError('Unsupported structured component')
        for j,piece in enumerate(pieces):
            piece.update(component_id=a['id'],assembly_kind=kind,role=piece.get('role',a['roles'][min(j,len(a['roles'])-1)]),
                         confidence=a.get('confidence',1.))
        graph['components'].extend(pieces)
    graph.update(component_assemblies=True, geometry_source=bundle.get('source'), shared_node_count=len(nodes),
                 shared_component_graph=bundle,model_restoration=bundle.get('source')=='image-model-prediction')
    return graph


def encode(bundle, text_vocab, template_vocab=None, coord_digits=6, measure_digits=5):
    """Variable sets; storage order is never query identity supervision."""
    nodes=np.asarray(bundle['nodes_mm'],np.float32)/UNIT; n=len(bundle['components'])
    kinds=np.zeros(n,np.int64); refs=np.full((n,MAX_REFS),-1,np.int64)
    params=np.zeros((n,PARAMS),np.float32); mask=np.zeros_like(params,dtype=bool)
    roles=np.zeros(n,np.int64); digits=np.full((n,5),-1,np.int64); text=np.full(n,-1,np.int64)
    hosts=np.full(n,-1,np.int64)
    template=np.full(n,-1,np.int64); template_vocab=template_vocab or {}
    bearing=np.full(n,-1,np.int64); size_digits=np.full((n,7,measure_digits),-1,np.int64); size_sign=np.full((n,7),-1,np.int64)
    for i,c in enumerate(bundle['components']):
        k=c['kind']; p=c['parameters']; kinds[i]=TYPES.index(k); refs[i,:len(c['nodes'])]=c['nodes']; roles[i]=c['roles'][0]; hosts[i]=c['host']
        values=[]
        if k=='dimension':
            angle=math.radians(p['angle_cad']); values=[math.sin(angle),math.cos(angle),p['dimension_kind']]
            val=int(round(p['value_mm']))
            if not 0<=val<=99999: raise ValueError('Dimension range unsupported')
            digits[i]=[int(x) for x in f'{val:05d}']
        elif k in ('swing_opening','circular_arc'):
            angle=math.radians(p['start_degrees']); values=[p['radius_mm']/UNIT,math.sin(angle),math.cos(angle),p['extent_degrees']/360,p['sweep']]
            if k=='swing_opening': values+=p['leaf_hinge_offset_ratio']+[p['leaf_length_ratio'],p['leaf_at'],p['leaf_angle_offset_degrees']/360]
        elif k=='wall_face_pair':
            angle=math.radians(p['angle_degrees']); values=[math.sin(angle),math.cos(angle),p['thickness_mm']/UNIT]
            values+= (np.asarray(p['face_extents_mm'])/UNIT).ravel().tolist()+p['face_signs']
        elif k=='rectangular_loop':
            angle=math.radians(p['angle_degrees']); values=[math.sin(angle),math.cos(angle),p['width_mm']/UNIT,p['height_mm']/UNIT]
        elif k=='native_path': values=[int(p['closed']),len(c['nodes'])/MAX_REFS]
        elif k=='text':
            values=[p['height_mm']/UNIT]; text[i]=text_vocab.get(p['text'],0)
        elif k=='native_symbol':
            values=[p['size_mm']/UNIT]; template[i]=template_vocab.get(p['template_id'],0)
        if values: params[i,:len(values)]=values; mask[i,:len(values)]=True
        angle_value=None; sizes=[]
        if k=='dimension':angle_value=p['angle_cad']
        elif k in ('swing_opening','circular_arc'):angle_value=p['start_degrees'];sizes=[p['radius_mm']]
        elif k=='wall_face_pair':angle_value=p['angle_degrees'];sizes=[p['thickness_mm']]+np.asarray(p['face_extents_mm']).ravel().tolist()
        elif k=='rectangular_loop':angle_value=p['angle_degrees'];sizes=[p['width_mm'],p['height_mm']]
        elif k=='native_symbol':sizes=[p['size_mm']]
        if angle_value is not None:
            cardinal=int(round(angle_value/90))%4
            difference=abs((angle_value-cardinal*90+180)%360-180)
            bearing[i]=cardinal if difference<.001 else 4
        for s,value in enumerate(sizes):
            rounded=int(round(abs(value)))
            if rounded<10**measure_digits:size_digits[i,s]=[int(x) for x in f'{rounded:0{measure_digits}d}'];size_sign[i,s]=int(value<0)
    axis=np.tile(np.arange(len(nodes)),(2,1))
    for d,groups in enumerate(bundle['axis_groups']):
        for group in groups: axis[d,group]=group[0]
    physical=nodes*UNIT;node_digits=np.asarray([[[int(x) for x in f'{int(round(abs(v)*10)):0{coord_digits}d}'] for v in point] for point in physical],np.int64)
    if node_digits.shape!=(len(nodes),2,coord_digits):raise ValueError('0.1mm coordinate vocabulary capacity exceeded')
    return dict(nodes=nodes,kind=kinds,refs=refs,params=params,param_mask=mask,role=roles,digits=digits,text=text,host=hosts,axis=axis,template=template,
                bearing=bearing,size_digits=size_digits,size_sign=size_sign,node_digits=node_digits,node_sign=(physical<0).astype(np.int64))


def decode_component(kind, params, digits, text_index, texts):
    p=np.asarray(params); angle=lambda s,c: math.degrees(math.atan2(float(s),float(c)))
    if kind=='dimension': return {'angle_cad':angle(*p[:2]),'dimension_kind':int(p[2]>.5),'value_mm':int(''.join(str(int(x)) for x in digits))}
    if kind in ('swing_opening','circular_arc'):
        result={'radius_mm':max(1.,abs(float(p[0]))*UNIT),'start_degrees':angle(*p[1:3]),
                'extent_degrees':float(np.clip(p[3]*360,1,359.99)),'sweep':int(p[4]>.5)}
        if kind=='swing_opening': result.update(leaf_hinge_offset_ratio=p[5:7].tolist(),leaf_length_ratio=max(.01,float(p[7])),
                                             leaf_at=int(p[8]>.5),leaf_angle_offset_degrees=float(p[9]*360))
        return result
    if kind=='wall_face_pair': return {'angle_degrees':angle(*p[:2]),'thickness_mm':max(1.,abs(float(p[2]))*UNIT),
                                      'face_extents_mm':(p[3:7].reshape(2,2)*UNIT).tolist(),'face_signs':[1 if v>=0 else -1 for v in p[7:9]]}
    if kind=='rectangular_loop': return {'angle_degrees':angle(*p[:2]),'width_mm':max(1.,abs(float(p[2]))*UNIT),'height_mm':max(1.,abs(float(p[3]))*UNIT)}
    if kind=='native_path': return {'closed':bool(p[0]>.5)}
    if kind=='text': return {'height_mm':max(1.,abs(float(p[0]))*UNIT),'text':texts[text_index]}
    return {}


def supplement_native_templates(bundle,graph):
    """Collapse small native multi-edge motifs, preserving every member.

    The library contains local part geometry (<=2.5m/256 primitives), never
    whole site plans. It is published from training examples only.
    """
    result=copy.deepcopy(bundle);source=graph['components'];groups={};allowed={'unresolved_edge','circular_arc','symbol','native_path'}
    for i,c in enumerate(result['components']):
        if c['kind'] not in allowed or not c['members']:continue
        parents={source[j].get('parent') for j in c['members']}
        if len(parents)==1 and None not in parents:groups.setdefault(next(iter(parents)),[]).append(i)
    removed=set(); added=[]; templates={}; nodes=result['nodes_mm']
    for parent,indices in groups.items():
        members=sorted({j for i in indices for j in result['components'][i]['members']})
        if not 2<=len(members)<=256:continue
        points=np.concatenate([to_mm(source[j]['points'],bundle['frame']) for j in members])
        lo,hi=points.min(0),points.max(0);size=float(max(hi-lo));center=(lo+hi)/2
        if not 1<=size<=2500:continue
        children=[{'kind':source[j]['kind'],'points':((to_mm(source[j]['points'],bundle['frame'])-center)/size).tolist(),'role':source[j].get('role',0)} for j in members]
        signature=hashlib.sha256(json.dumps([{**c,'points':np.round(c['points'],8).tolist()} for c in children],sort_keys=True).encode()).hexdigest()
        templates[signature]=children;node=len(nodes);nodes.append(center.tolist())
        added.append({'id':'N'+signature[:10]+str(len(added)),'kind':'native_symbol','nodes':[node],
                      'parameters':{'size_mm':size,'template_id':signature},'members':members,
                      'roles':[c['role'] for c in children],'host':-1,'host_status':'unknown',
                      'semantic_status':'local-native-pattern;not-confirmed-business-object','native_parent':parent})
        removed.update(indices)
    # Remap host indices after compaction; keep the shared-coordinate graph.
    kept=[(i,c) for i,c in enumerate(result['components']) if i not in removed]
    mapping={old:new for new,(old,c) in enumerate(kept)}
    result['components']=[c for _,c in kept]+added
    for c in result['components']:c['host']=mapping.get(c.get('host',-1),-1)
    used=sorted({n for c in result['components'] for n in c['nodes']}); remap={n:i for i,n in enumerate(used)}
    result['nodes_mm']=[nodes[i] for i in used]
    for c in result['components']:c['nodes']=[remap[n] for n in c['nodes']]
    axes=[]
    for axis in (0,1):
        buckets={}
        for i,p in enumerate(result['nodes_mm']):buckets.setdefault(round(p[axis],3),[]).append(i)
        axes.append([ids for ids in buckets.values() if len(ids)>1])
    result.update(axis_groups=axes,templates=templates,native_local_templates_only=True)
    return result
