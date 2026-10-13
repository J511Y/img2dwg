"""DINOv3 frozen encoder + dense typed component/endpoint regression decoder.

The heatmap finds component centers. The output is coordinate regression, not
binary-mask tracing. Native dimensions and block envelopes have separate heads.
"""
from __future__ import annotations
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from transformers import AutoModel, AutoConfig
from img2dwg.vector import KINDS, ROLES

BACKBONE='facebook/dinov3-vitb16-pretrain-lvd1689m'
REVISION='5931719e67bbdb9737e363e781fb0c67687896bc'
STRIDE=4

def conv(a,b,stride=1):
    return nn.Sequential(nn.Conv2d(a,b,3,stride=stride,padding=1),nn.GroupNorm(8,b),nn.GELU())

class VectorModel(nn.Module):
    def __init__(self, pretrained=True, backbone_config=None, slots=1):
        super().__init__()
        self.slots=slots; channels=len(KINDS)*slots
        self.encoder=AutoModel.from_pretrained(BACKBONE,revision=REVISION) if pretrained else AutoModel.from_config(AutoConfig.for_model('dinov3_vit',**backbone_config))
        self.encoder.requires_grad_(False); hidden=self.encoder.config.hidden_size
        self.low=nn.Sequential(conv(3,32,2),conv(32,64,2),conv(64,64))
        self.context=nn.Sequential(nn.Conv2d(hidden,128,1),nn.GELU())
        self.decode=nn.Sequential(conv(192,128),conv(128,128),conv(128,64))
        self.centers=nn.Conv2d(64,channels,1)
        self.coords=nn.Conv2d(64,channels*6,1)
        self.roles=nn.Conv2d(64,channels*len(ROLES),1)
        nn.init.constant_(self.centers.bias,-2.19)
        self.register_buffer('mean',torch.tensor([.485,.456,.406])[None,:,None,None])
        self.register_buffer('std',torch.tensor([.229,.224,.225])[None,:,None,None])
    def train(self,mode=True):
        super().train(mode); self.encoder.eval(); return self
    def forward(self,image):
        with torch.no_grad():
            out=self.encoder(pixel_values=(image-self.mean)/self.std)
            h,w=image.shape[-2]//16,image.shape[-1]//16
            # CLS and register tokens precede the spatial patch tokens.
            tokens=out.last_hidden_state[:,-h*w:]
            features=tokens.transpose(1,2).reshape(len(image),-1,h,w)
        low=self.low(image); context=F.interpolate(self.context(features),size=low.shape[-2:],mode='bilinear',align_corners=False)
        x=self.decode(torch.cat((low,context),1))
        channels=len(KINDS)*self.slots
        return {'centers':self.centers(x),'coords':self.coords(x).reshape(len(x),channels,6,*x.shape[-2:]),
                'roles':self.roles(x).reshape(len(x),channels,len(ROLES),*x.shape[-2:])}

def targets(graph,size,slots=1,canonical=False):
    channels=len(KINDS)*slots
    s=size//STRIDE; heat=np.zeros((channels,s,s),np.float32)
    coords=np.zeros((channels,6,s,s),np.float32); roles=np.full((channels,s,s),-1,np.int64)
    mask=np.zeros_like(heat); collisions=0; kept=0
    for c in sorted(graph['components'],key=lambda c:-np.linalg.norm(np.array(c['points'][1])-c['points'][0])):
        kind=KINDS.index(c['kind']); p=np.asarray(c['points'],np.float32).copy()
        end=2 if kind==1 else 1
        if canonical and tuple(np.round(p[0],2))>tuple(np.round(p[end],2)):
            p[[0,end]]=p[[end,0]]
        center=(p[0]+p[end])/2
        x,y=np.floor(center/STRIDE).astype(int)
        if not(0<=x<s and 0<=y<s): continue
        k=next((kind*slots+i for i in range(slots) if not mask[kind*slots+i,y,x]),None)
        if k is None: collisions+=1; continue
        # Small Gaussian excludes adjacent cells from background penalty.
        for dy in range(-2,3):
            for dx in range(-2,3):
                if 0<=y+dy<s and 0<=x+dx<s: heat[k,y+dy,x+dx]=max(heat[k,y+dy,x+dx],math.exp(-(dx*dx+dy*dy)/2))
        heat[k,y,x]=1; mask[k,y,x]=1
        origin=np.array([(x+.5)*STRIDE,(y+.5)*STRIDE])
        coords[k,:,y,x]=((p-origin)/size).ravel(); roles[k,y,x]=int(c.get('role',0)); kept+=1
    return {k:torch.from_numpy(v) for k,v in {'heat':heat,'coords':coords,'roles':roles,'mask':mask}.items()},kept,collisions

def loss(pred,target):
    prob=pred['centers'].sigmoid().clamp(1e-5,1-1e-5); gt=target['heat']; pos=gt.eq(1); neg=gt.lt(1)
    denominator=pos.sum().clamp(min=1)
    center=(-(prob.log()*(1-prob)**2*pos)-((1-prob).log()*prob**2*(1-gt)**4*neg)).sum()/denominator
    mask=target['mask']; regression=(F.smooth_l1_loss(pred['coords'],target['coords'],reduction='none',beta=.02)*mask[:,:,None]).sum()/(mask.sum().clamp(min=1)*6)
    role_loss=F.cross_entropy(pred['roles'].permute(0,1,3,4,2).reshape(-1,len(ROLES)),target['roles'].reshape(-1),ignore_index=-1)
    return center+20*regression+.2*role_loss,{'center':float(center.detach()),'coordinate':float(regression.detach()),'role':float(role_loss.detach())}

def decode(pred,size,threshold=.25,limit=2000):
    hm=pred['centers'][0].sigmoid(); hm=hm*(hm==F.max_pool2d(hm[None],3,1,1)[0])
    scores,flat=hm.flatten().topk(min(limit,hm.numel())); s=size//STRIDE
    components=[]; seen=set(); slots=hm.shape[0]//len(KINDS)
    for confidence,index in zip(scores.detach().cpu().tolist(),flat.cpu().tolist()):
        if confidence<threshold: break
        channel=index//(s*s); k=channel//slots; y=(index//s)%s; x=index%s
        offset=pred['coords'][0,channel,:,y,x].detach().float().cpu().numpy().reshape(3,2)
        p=offset*size+[(x+.5)*STRIDE,(y+.5)*STRIDE]
        if not np.isfinite(p).all() or (p < -size*.02).any() or (p>size*1.02).any(): continue
        p=np.clip(p,0,size)
        endpoints=p[[0,2]] if k==1 else p[:2]
        if np.linalg.norm(endpoints[1]-endpoints[0])<2: continue
        # Equivalent segment directions deduplicate without forcing right angles.
        rounded=[tuple(np.round(q/2).astype(int)) for q in endpoints]
        key=(k,tuple(sorted(rounded)))
        # Two semicircles can share endpoints; dimension layout can differ too.
        if k in (1,2): key=(*key,tuple(np.round(p[1 if k==1 else 2]/2).astype(int)))
        if key in seen: continue
        seen.add(key); r=int(pred['roles'][0,channel,:,y,x].argmax())
        components.append({'kind':KINDS[k],'points':p.tolist(),'role':r,'confidence':confidence,
            'semantic_status':'unresolved' if r==0 else 'layer-role-candidate',
            **({'value_text':'?','measurement_status':'unread-unassociated'} if k==2 else {})})
    # Graph nodes are deterministic endpoint-neighborhood proposals, not approved topology.
    nodes=[]; edges=[]; bins={}
    for c in components:
        if c['kind']!='segment': continue
        ids=[]
        for p in c['points'][:2]:
            cell=(math.floor(p[0]/2),math.floor(p[1]/2))
            candidates=sorted(i for dx in (-1,0,1) for dy in (-1,0,1) for i in bins.get((cell[0]+dx,cell[1]+dy),[]))
            found=next((i for i in candidates if np.linalg.norm(np.array(p)-nodes[i])<2),None)
            if found is None:
                found=len(nodes); nodes.append(p); bins.setdefault(cell,[]).append(found)
            ids.append(found)
        edges.append(ids)
    return {'schema':'img2dwg-vector/v1','canvas':[size,size],'units':'unitless','scale':1.,
        'components':components,'nodes':nodes,'edges':edges,
        'geometry_source':'trained-coordinate-decoder','dimension_status':'unread-unassociated',
        'review_required':True,'exclusive_unit_scope':'user-selected-input-roi',
        'topology_status':'endpoint-neighborhood-proposals;not-validated'}
