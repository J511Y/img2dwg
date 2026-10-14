"""Typed vector proposals, a raster-free SVG viewer, and an editable DXF factory."""
from __future__ import annotations
import hashlib, html, json, math
from pathlib import Path
import ezdxf
import numpy as np

KINDS = ('segment', 'arc', 'dimension', 'symbol')
ROLES = ('unresolved', 'centerline_candidate', 'wall_candidate', 'door_candidate',
         'window_candidate', 'fixture_candidate')
COLORS = ('#273449', '#e39b12', '#1a9b78', '#db577d', '#4f83dc', '#936ad4')

def cross2(a,b):
    return float(a[0]*b[1]-a[1]*b[0])

def role(layer):
    s = layer.upper()
    if 'CEN' in s: return 1
    if 'DOOR' in s or '도어' in s: return 3
    if 'WIN' in s: return 4
    if 'FUR' in s or 'INS' == s: return 5
    if 'WAL' in s or s in ('A-CON','A-FIN','GYP','COL','경량'): return 2
    return 0

def arc_parameters(points):
    a,b,c = np.asarray(points, dtype=float).reshape(3,2)
    cross = cross2(b-a,c-a)
    if abs(float(cross)) < 1e-8: return None
    center = np.linalg.solve(2*np.stack((b-a,c-a)),
                            np.array([b@b-a@a,c@c-a@a]))
    radius = float(np.linalg.norm(a-center))
    angles = [math.degrees(math.atan2(*(p-center)[::-1]))%360 for p in (a,b,c)]
    # Coordinates are image-down. The SVG sweep goes through the middle point.
    span = (angles[2]-angles[0])%360
    sweep = int((angles[1]-angles[0])%360 <= span)
    extent = span if sweep else 360-span
    return center, radius, angles, sweep, extent

def validate_graph(graph):
    if graph.get('schema') != 'img2dwg-vector/v1': raise ValueError('Unknown vector schema')
    for item in graph['components']:
        if item['kind'] not in KINDS: raise ValueError('Unsupported component')
        p = np.asarray(item['points'], dtype=float)
        if p.shape != (3,2) or not np.isfinite(p).all(): raise ValueError('Invalid coordinates')
        if not 0 <= int(item.get('role',0)) < len(ROLES): raise ValueError('Invalid role')
    if not math.isfinite(float(graph['scale'])) or graph['scale'] <= 0:
        raise ValueError('Invalid scale')

def svg(graph):
    validate_graph(graph)
    w,h = graph['canvas']
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="100%" role="img" aria-label="모델 예측 벡터">',
           f'<rect width="{w}" height="{h}" fill="white"/>',
           '<g fill="none" stroke-width="1.3" vector-effect="non-scaling-stroke">']
    for e in graph['components']:
        p = np.asarray(e['points']); color = COLORS[e.get('role',0)]
        title = html.escape(f"{e['kind']} · {ROLES[e.get('role',0)]} · {e.get('confidence',1):.3f}")
        out.append(f'<g stroke="{color}"><title>{title}</title>')
        if e['kind']=='arc' and (a:=arc_parameters(p)) is not None:
            _,r,_,sweep,extent=a
            out.append(f'<path d="M {p[0,0]:.4f} {p[0,1]:.4f} A {r:.4f} {r:.4f} 0 {int(extent>180)} {sweep} {p[2,0]:.4f} {p[2,1]:.4f}"/>')
        elif e['kind']=='symbol':
            x,y=np.minimum(p[0],p[1]); dx,dy=np.abs(p[1]-p[0])
            out.append(f'<rect x="{x:.4f}" y="{y:.4f}" width="{dx:.4f}" height="{dy:.4f}" stroke-dasharray="3 3"/>')
        elif e['kind']=='dimension':
            d=p[1]-p[0]; length=np.linalg.norm(d)
            if length>1e-6:
                n=np.array([-d[1],d[0]])/length; offset=float((p[2]-(p[0]+p[1])/2)@n)
                q=p[:2]+n*offset
                out.append(f'<path d="M {p[0,0]:.4f} {p[0,1]:.4f} L {q[0,0]:.4f} {q[0,1]:.4f} L {q[1,0]:.4f} {q[1,1]:.4f} L {p[1,0]:.4f} {p[1,1]:.4f}" stroke-dasharray="2 2"/>')
                value = e.get('value_text','?')
                out.append(f'<text x="{p[2,0]:.4f}" y="{p[2,1]:.4f}" font-size="8" fill="{color}" stroke="none">{html.escape(str(value))}</text>')
        else:
            out.append(f'<path d="M {p[0,0]:.4f} {p[0,1]:.4f} L {p[1,0]:.4f} {p[1,1]:.4f}"/>')
        out.append('</g>')
    out.append('</g>')
    for position,text in graph.get('texts',[]):
        out.append(f'<text x="{position[0]:.4f}" y="{position[1]:.4f}" font-size="8" fill="#273449">{html.escape(str(text))}</text>')
    out.append('</svg>')
    return ''.join(out)

def write_dxf(graph, path):
    validate_graph(graph)
    doc=ezdxf.new('R2018'); doc.units=4 if graph['units']=='mm' else 0
    ms=doc.modelspace(); scale=float(graph['scale']); height=graph['canvas'][1]
    def xy(p): return (float(p[0])*scale,(height-float(p[1]))*scale)
    for i,name in enumerate(ROLES): doc.layers.new(name,dxfattribs={'color':i+1})
    compiled_assemblies=set(); assembly_templates={}
    if graph.get('component_assemblies'):
        # Parameter factories become real reusable BLOCK/INSERT components.
        # This consumes generated geometry and parameters, never source CAD.
        doc.appids.new('IMG2DWG_COMPONENT')
        for assembly in graph.get('assemblies',[]):
            kind=assembly['kind']; params=assembly['parameters']
            if kind not in ('swing_opening','rectangular_loop','wall_face_pair','native_path','native_symbol'): continue
            pieces=[c for c in graph['components'] if c.get('component_id')==assembly['id']]
            if not pieces: continue
            if kind=='swing_opening':
                origin_mm=np.asarray(params['hinge_mm']); angle=-params['start_degrees']
                sx=sy=params['radius_mm']
            elif kind=='rectangular_loop':
                origin_mm=np.asarray(params['center_mm']); angle=-params['angle_degrees']
                sx,sy=params['width_mm'],params['height_mm']
            elif kind=='wall_face_pair':
                origin_mm=np.asarray(params['spine_origin_mm']); angle=-params['angle_degrees']
                sx=max(max(x) for x in params['face_extents_mm'])-min(min(x) for x in params['face_extents_mm'])
                sy=params['thickness_mm']
            else:
                origin_mm=np.asarray(params['origin_mm']); angle=0.; sx=sy=params.get('size_mm',1.)
            if min(sx,sy)<=1e-8: raise ValueError('Invalid component dimensions')
            origin=np.array([origin_mm[0]+graph['canvas'][0]*scale/2,height*scale/2-origin_mm[1]])
            radians=math.radians(angle); rotation=np.array([[math.cos(radians),-math.sin(radians)],
                                                           [math.sin(radians),math.cos(radians)]])
            def local(q): return ((np.asarray(xy(q))-origin)@rotation)/[sx,sy]
            normalized=[]
            for piece in pieces:
                if piece['kind']=='symbol':continue
                normalized.append({'kind':piece['kind'],'points':[local(p).tolist() for p in piece['points']],
                                   'role':piece.get('role',0)})
            signature=hashlib.sha256(json.dumps({'kind':kind,'geometry':[
                {**c,'points':np.round(c['points'],10).tolist()} for c in normalized]},sort_keys=True).encode()).hexdigest()[:16]
            name=f'{kind}_{signature}'
            if name not in assembly_templates:
                block=doc.blocks.new(name)
                for child in normalized:
                    q=np.asarray(child['points']); ca={'layer':ROLES[child['role']]}
                    if child['kind']=='segment': block.add_line(q[0],q[1],dxfattribs=ca)
                    elif child['kind']=='arc':
                        # Door inserts use uniform scale; no elliptical arc approximation.
                        a=arc_parameters(q)
                        if a is None: raise ValueError('Invalid component arc')
                        center,r,angles,sweep,_=a
                        # local() returns CAD y-up, so angles are already CAD angles.
                        start,end=(angles[0],angles[2]) if sweep else (angles[2],angles[0])
                        block.add_arc(center,r,start,end,dxfattribs=ca)
                    else: raise ValueError('Unsupported component child')
                assembly_templates[name]=True
            insert=ms.add_blockref(name,origin,dxfattribs={'xscale':sx,'yscale':sy,'rotation':angle,
                                  'layer':ROLES[pieces[0].get('role',0)]})
            insert.set_xdata('IMG2DWG_COMPONENT',[(1000,kind),(1000,assembly['id'])])
            compiled_assemblies.add(assembly['id'])
    block_children={}
    for e in graph['components']:
        if e['kind']!='symbol' and e.get('parent'):
            block_children.setdefault(e['parent'],[]).append(e)
    exported_children={e.get('parent') for e in graph['components'] if e['kind']=='symbol' and block_children.get(e.get('parent'))}
    for i,e in enumerate(graph['components']):
        if e.get('component_id') in compiled_assemblies: continue
        if e.get('parent') in exported_children and e['kind']!='symbol': continue
        p=np.asarray(e['points']); attrs={'layer':ROLES[e.get('role',0)]}
        if e['kind']=='arc' and (a:=arc_parameters(p)) is not None:
            center,r,angles,sweep,_=a
            start,end=((-angles[2])%360,(-angles[0])%360) if sweep else ((-angles[0])%360,(-angles[2])%360)
            ms.add_arc(xy(center),r*scale,start,end,dxfattribs=attrs)
        elif e['kind']=='dimension':
            if np.linalg.norm(p[1]-p[0])<1e-5: continue
            override={'dimtxt':max(scale*7,1e-3),'dimasz':max(scale*3,1e-3)}
            if e.get('dimension_kind')==0:
                dim=ms.add_linear_dim(base=xy(p[2]),p1=xy(p[0]),p2=xy(p[1]),angle=e['angle_cad'],
                    text=str(e.get('value_text','?')),dxfattribs=attrs,override=override)
            else:
                dim=ms.add_aligned_dim(p1=xy(p[0]),p2=xy(p[1]),
                    distance=cross2(p[1]-p[0],p[2]-p[0])/np.linalg.norm(p[1]-p[0])*-scale,
                    text=str(e.get('value_text','?')),dxfattribs=attrs,override=override)
            dim.render()
        elif e['kind']=='symbol':
            children=block_children.get(e.get('parent'),[])
            if children:
                name=f'INSTANCE_{i}'; block=doc.blocks.new(name); origin=np.asarray(xy(p[2]))
                for child in children:
                    q=np.asarray(child['points']); ca={'layer':ROLES[child.get('role',0)]}
                    if child['kind']=='segment': block.add_line(np.asarray(xy(q[0]))-origin,np.asarray(xy(q[1]))-origin,dxfattribs=ca)
                    elif child['kind']=='arc' and (a:=arc_parameters(q)) is not None:
                        center,r,angles,sweep,_=a
                        start,end=((-angles[2])%360,(-angles[0])%360) if sweep else ((-angles[0])%360,(-angles[2])%360)
                        block.add_arc(np.asarray(xy(center))-origin,r*scale,start,end,dxfattribs=ca)
                ms.add_blockref(name,origin,dxfattribs=attrs); exported_children.add(e['parent']); continue
            # A predicted envelope is explicitly unresolved, never a recovered fixture.
            a,b=xy(p[0]),xy(p[1]); ms.add_lwpolyline([a,(a[0],b[1]),b,(b[0],a[1])],close=True,dxfattribs=attrs)
        else: ms.add_line(xy(p[0]),xy(p[1]),dxfattribs=attrs)
    for position, text in graph.get('texts', []):
        ms.add_mtext(str(text),dxfattribs={'insert':xy(position),'char_height':max(scale*9,1.),'layer':ROLES[0]})
    doc.saveas(path)
    reopened=ezdxf.readfile(path); audit=reopened.audit()
    if audit.has_errors: raise ValueError('DXF audit failed')
    return {'entities':len(reopened.modelspace()),'units':int(reopened.units),
            'dimension_count':len(reopened.modelspace().query('DIMENSION')),
            'block_instances':len(reopened.modelspace().query('INSERT')),
            'dimension_max_error_mm':max((abs(float(e.get_measurement())-c['measurement_mm']) for e,c in
               zip(reopened.modelspace().query('DIMENSION'),(c for c in graph['components'] if c['kind']=='dimension')) if 'measurement_mm' in c),default=0),
            'audit_errors':len(audit.errors)}

def exports(graph, folder):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    (folder/'prediction.svg').write_text(svg(graph),encoding='utf-8')
    (folder/'prediction.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf-8')
    receipt=write_dxf(graph,folder/'prediction.dxf')
    return receipt
