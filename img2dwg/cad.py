"""CAD supervision: native dimensions/instances remain components, not picture lines."""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import ezdxf
from ezdxf import disassemble, bbox
from PIL import Image, ImageDraw, ImageFont
from img2dwg.vector import role, KINDS

def extract(path, bounds, size=768, min_length_pixels=2):
    doc=ezdxf.readfile(path); x0,y0,x1,y1=map(float,bounds)
    factor=(size-48)/max(x1-x0,y1-y0)
    offset=np.array([(size-(x1-x0)*factor)/2,(size-(y1-y0)*factor)/2])
    def pixel(p): return np.array([(float(p[0])-x0)*factor,(y1-float(p[1]))*factor])+offset
    components=[]; counts={}; skipped={}; texts=[]
    def add(kind,points,e,parent=None):
        p=np.asarray([pixel(q) for q in points]);
        if not np.isfinite(p).all() or (p<15).any() or (p>size-15).any(): return
        if np.linalg.norm((p[2] if kind=='arc' else p[1])-p[0])<min_length_pixels: return
        if kind=='arc':
            from img2dwg.vector import arc_parameters
            if arc_parameters(p) is None:
                skipped['degenerate-native-arc']=skipped.get('degenerate-native-arc',0)+1
                return
        if kind=='segment' and tuple(p[0])>tuple(p[1]): p=p[[1,0,2]]
        components.append({'kind':kind,'points':p.tolist(),'role':role(e.dxf.layer),
            'source_id':e.dxf.get('handle','virtual'),'parent':parent,'confidence':1.,
            'semantic_status':'layer-role-candidate' if role(e.dxf.layer) else 'unresolved'})
    def geometry(e,parent=None):
        t=e.dxftype()
        if t=='LINE':
            a,b=e.dxf.start,e.dxf.end; add('segment',[a,b,(a+b)/2],e,parent)
        elif t=='ARC':
            c=e.dxf.center; a=float(e.dxf.start_angle); span=(float(e.dxf.end_angle)-a)%360
            points=[(c.x+e.dxf.radius*math.cos(math.radians(v)),c.y+e.dxf.radius*math.sin(math.radians(v))) for v in [a,a+span/2,a+span]]
            add('arc',points,e,parent)
        elif t=='CIRCLE':
            c=e.dxf.center; r=e.dxf.radius
            for a in [0,180]:
                pts=[(c.x+r*math.cos(math.radians(v)),c.y+r*math.sin(math.radians(v))) for v in [a,a+90,a+180]]
                add('arc',pts,e,parent)
        elif t in ('LWPOLYLINE','POLYLINE','MLINE'):
            try:
                for v in e.virtual_entities(): geometry(v,parent or e.dxf.handle)
            except Exception: skipped[t]=skipped.get(t,0)+1
        elif t in ('TEXT','MTEXT'):
            p=pixel(e.dxf.insert)
            if (p>0).all() and (p<size).all(): texts.append((p.tolist(),e.plain_text() if t=='MTEXT' else e.dxf.text))
        elif t=='INSERT':
            # Preserve the instance identity and its internal geometry, never all definitions.
            try:
                box=bbox.extents([e],fast=True)
                if box.has_data:
                    a,b=box.extmin,box.extmax
                    add('symbol',[a,b,(a+b)/2],e,e.dxf.handle)
                for v in disassemble.recursive_decompose([e]): geometry(v,e.dxf.handle)
            except Exception: skipped[t]=skipped.get(t,0)+1
        else: skipped[t]=skipped.get(t,0)+1
    for e in doc.modelspace():
        counts[e.dxftype()]=counts.get(e.dxftype(),0)+1
        if e.dxftype()=='DIMENSION':
            # Restrict first decoder to native linear/aligned dimensions.
            if e.dxf.dimtype&15 not in (0,1): skipped['dimension-kind']=skipped.get('dimension-kind',0)+1; continue
            a,b,c=e.dxf.get('defpoint2'),e.dxf.get('defpoint3'),e.dxf.get('text_midpoint')
            if a is not None and b is not None and c is not None:
                before=len(components); add('dimension',[a,b,c],e)
                if len(components)>before:
                    value=e.get_measurement(); components[-1]['value_text']=str(round(float(value)))
                    components[-1]['measurement_mm']=float(value)
                    components[-1]['dimension_kind']=e.dxf.dimtype&15
                    components[-1]['angle_cad']=float(e.dxf.get('angle',0))
        else: geometry(e)
    # Canonical ordering is geometric, never source handle/storage order.
    components.sort(key=lambda c:(KINDS.index(c['kind']),c['points']))
    unique=[]; seen=set()
    for c in components:
        sig=(c['kind'],tuple(np.round(np.asarray(c['points']).ravel(),3)))
        if c['kind']=='dimension':
            # Native annotations may share geometry but have distinct styles
            # or instances. Geometry dedup must never discard required DIMs.
            sig+=(c['source_id'],c['dimension_kind'],c['measurement_mm'],c['angle_cad'])
        if sig not in seen: seen.add(sig); unique.append(c)
    return {'schema':'img2dwg-vector/v1','canvas':[size,size],'scale':1/factor,'units':'mm',
            'components':unique,'texts':texts,'source_counts':counts,'skipped_types':skipped,
            'scope':'before-plan-panel;exclusive-unit-semantic-boundary-unverified',
            'dimension_associations':'unresolved','native_component_identity_preserved':True}

def render(graph):
    size=graph['canvas'][0]; image=Image.new('RGB',(size,size),'white'); d=ImageDraw.Draw(image)
    for c in graph['components']:
        p=np.asarray(c['points']); pts=[tuple(q) for q in p]
        if c['kind']=='segment': d.line(pts[:2],fill='black',width=1)
        elif c['kind']=='arc':
            from img2dwg.vector import arc_parameters
            a=arc_parameters(p)
            if a is not None:
                center,r,angles,sweep,extent=a
                angles=np.linspace(angles[0],angles[0]+(extent if sweep else -extent),max(8,int(extent/3)))
                q=center+np.stack([np.cos(np.radians(angles)),np.sin(np.radians(angles))],1)*r
                d.line([tuple(x) for x in q],fill='black',width=1)
        elif c['kind']=='dimension':
            v=p[1]-p[0]; length=np.linalg.norm(v)
            if length>0:
                n=np.array([-v[1],v[0]])/length; off=(p[2]-(p[0]+p[1])/2)@n
                q=p[:2]+n*off
                d.line([pts[0],tuple(q[0]),tuple(q[1]),pts[1]],fill='#555555',width=1)
                d.text(pts[2],c.get('value_text','?'),fill='black',font=ImageFont.load_default(size=9))
        # Envelopes are targets only; draw their actual internal geometry above.
    for p,t in graph.get('texts',[]):
        d.text(tuple(p),t[:50],fill='#555555',font=ImageFont.load_default(size=9))
    return image
