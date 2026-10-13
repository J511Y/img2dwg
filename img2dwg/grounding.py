"""Observed straight-line proposals and rejection of unsupported model geometry.

These are image evidence proposals, not metric CAD restoration or CAD retrieval.
"""
import math
import cv2
import numpy as np
from PIL import Image

def normalized_gray(image):
    gray=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    background=cv2.GaussianBlur(gray,(0,0),15)
    return np.clip(gray.astype(np.float32)/(background.astype(np.float32)+1)*255,0,255).astype(np.uint8)

def observed_lines(image,min_length=12,limit=1800):
    gray=normalized_gray(image)
    result=cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(gray)[0]
    if result is None: return np.empty((0,2,2),np.float32),gray
    lines=np.asarray(result).reshape(-1,2,2)
    lengths=np.linalg.norm(lines[:,1]-lines[:,0],axis=1)
    lines=lines[lengths>=min_length]; lengths=lengths[lengths>=min_length]
    return lines[np.argsort(-lengths)[:limit]],gray

def support_map(image):
    gray=normalized_gray(image)
    ink=(gray<205).astype(np.uint8)
    return cv2.distanceTransform(1-ink,cv2.DIST_L2,3)

def path_support(points,distance,max_distance=2.):
    points=np.asarray(points); h,w=distance.shape
    inside=(points[:,0]>=0)&(points[:,0]<w)&(points[:,1]>=0)&(points[:,1]<h)
    if not inside.all(): return float(inside.mean())*0.01
    xy=np.rint(points).astype(int); xy[:,0]=np.clip(xy[:,0],0,w-1); xy[:,1]=np.clip(xy[:,1],0,h-1)
    return float((distance[xy[:,1],xy[:,0]]<=max_distance).mean())

def component_support(c,distance):
    p=np.asarray(c['points']); kind=c['kind']
    if kind=='segment':
        q=p[0]+np.linspace(0,1,max(8,int(np.linalg.norm(p[1]-p[0]))))[:,None]*(p[1]-p[0])
    elif kind=='arc':
        from img2dwg.vector import arc_parameters
        arc=arc_parameters(p)
        if arc is None: return 0.
        center,r,angles,sweep,extent=arc
        # Reject enormous/full-circle artifacts before tessellation allocation.
        if r>max(distance.shape)*3 or r*math.radians(extent)>max(distance.shape)*3: return 0.
        a=np.linspace(angles[0],angles[0]+(extent if sweep else -extent),max(16,min(2048,int(r*math.radians(extent)))))
        q=center+np.stack((np.cos(np.radians(a)),np.sin(np.radians(a))),1)*r
    else: return 0.
    return path_support(q,distance)

def assess(graph,image):
    distance=support_map(image)
    scores=[component_support(c,distance) for c in graph['components'] if c['kind'] in ('segment','arc')]
    return {'protocol':'observed-ink-distance<=2px;curve-full-path-within-canvas;not-dimension-accuracy',
            'supported_fraction':float(np.mean(np.asarray(scores)>=.8)) if scores else 0.,
            'mean_path_support':float(np.mean(scores)) if scores else 0.,
            'components_checked':len(scores),'restoration_passed':False}

def baseline_graph(image,min_length=12):
    lines,gray=observed_lines(image,min_length)
    components=[]
    for p in lines:
        if tuple(p[0])>tuple(p[1]): p=p[::-1]
        components.append({'kind':'segment','points':[p[0].tolist(),p[1].tolist(),p.mean(0).tolist()],
            'role':0,'confidence':1.,'semantic_status':'unresolved;observed-image-stroke',
            'confidence_authority':'detector-presence;not-model-probability',
            'source':'opencv-LSD;not-trained-coordinate-prediction'})
    return {'schema':'img2dwg-vector/v1','canvas':list(image.size),'units':'unitless','scale':1.,
        'components':components,'geometry_source':'observed-line-detection-baseline',
        'review_required':True,'numeric_dimensions_verified':False,
        'exclusive_unit_scope':'caller-provided-region;not-automatically-confirmed',
        'dimension_status':'unread-unassociated','canonical_geometry_restored':False}
