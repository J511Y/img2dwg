"""Image-conditioned node/component sets with explicit reference and host heads.

Hungarian assignments are computed per example; no source handle or storage
index is a query identity. The forward pass never accepts target coordinates.
"""
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from scipy.optimize import linear_sum_assignment
from img2dwg.structured import TYPES, MAX_REFS, PARAMS, UNIT, decode_component

DEFAULT_LOSS_WEIGHTS=dict(node=100,node_precision=1,proposal=40,node_objectness=1,type=1,pointer=1,
                         parameter=20,role=.2,numeric=1,text=.3,template=1,bearing=1,scalar=1,
                         axis=.3,host=.3,dimension=4,count=1)


class SharedGraphDecoder(nn.Module):
    def __init__(self, nodes, components, texts=1, hidden=192, input_dim=768, templates=1,coord_digits=6,measure_digits=5,adaptive_capacity=False,minimum_nodes=32,minimum_components=32):
        super().__init__(); self.nodes=nodes; self.components=components; self.hidden=hidden
        self.coord_digits=coord_digits;self.measure_digits=measure_digits;self.adaptive_capacity=adaptive_capacity
        self.minimum_nodes=minimum_nodes;self.minimum_components=minimum_components
        self.node_queries=nn.Embedding(nodes,hidden); self.component_queries=nn.Embedding(components,hidden)
        self.image=nn.Linear(input_dim,hidden)
        self.condition=nn.Sequential(nn.Linear(input_dim*2,hidden*2),nn.GELU(),nn.Linear(hidden*2,hidden*2))
        self.image_attention=nn.MultiheadAttention(hidden,6,batch_first=True)
        self.node_mlp=nn.Sequential(nn.Linear(hidden,hidden*2),nn.GELU(),nn.Linear(hidden*2,hidden),nn.GELU())
        self.component_mlp=nn.Sequential(nn.Linear(hidden*2,hidden*2),nn.GELU(),nn.Linear(hidden*2,hidden),nn.GELU())
        self.node_xy=nn.Linear(hidden,2); self.node_active=nn.Linear(hidden,1)
        self.node_digits=nn.Linear(hidden,2*coord_digits*10);self.node_sign=nn.Linear(hidden,2*2)
        self.anchor_xy=nn.Linear(hidden,MAX_REFS*2)
        self.ref_queries=nn.Linear(hidden,MAX_REFS*hidden//3); self.ref_keys=nn.Linear(hidden,hidden//3)
        self.kind=nn.Linear(hidden,len(TYPES)+1); self.params=nn.Linear(hidden,PARAMS)
        self.role=nn.Linear(hidden,6); self.digits=nn.Linear(hidden,50); self.text=nn.Linear(hidden,texts)
        self.template=nn.Linear(hidden,templates)
        self.bearing=nn.Linear(hidden,5); self.size_digits=nn.Linear(hidden,7*measure_digits*10); self.size_sign=nn.Linear(hidden,7*2)
        self.count=nn.Sequential(nn.Linear(input_dim*2,hidden),nn.GELU(),nn.Linear(hidden,2))
        self.count[-1].bias.data.fill_(math.log(900.))
        self.host_query=nn.Linear(hidden,hidden//3); self.host_key=nn.Linear(hidden,hidden//3)
        self.axis_query=nn.Linear(hidden,hidden//3*2); self.axis_key=nn.Linear(hidden,hidden//3*2)
        side=math.ceil(math.sqrt(nodes)); grid=torch.stack(torch.meshgrid(torch.linspace(-.8,.8,side),torch.linspace(-.8,.8,side),indexing='ij'),-1).reshape(-1,2)[:nodes]
        self.register_buffer('node_grid',grid); nn.init.zeros_(self.node_xy.weight); nn.init.zeros_(self.node_xy.bias)
        cside=math.ceil(math.sqrt(components))
        cgrid=torch.stack(torch.meshgrid(torch.linspace(-.8,.8,cside),torch.linspace(-.8,.8,cside),indexing='ij'),-1).reshape(-1,2)[:components]
        self.register_buffer('component_grid',cgrid); nn.init.zeros_(self.anchor_xy.weight); nn.init.zeros_(self.anchor_xy.bias)
        # This is a fixed spatial prior, never per-site target initialization.
    def forward(self, features,capacities=None):
        b=features.shape[0]; pooled=torch.cat((features.mean(1),features.amax(1)),-1)
        log_count=self.count(pooled);n_count=self.nodes;c_count=self.components
        if self.adaptive_capacity or capacities is not None:
            if capacities is None and b!=1:raise ValueError('Inferred variable capacity requires a single image')
            if capacities is None:
                capacity=(log_count[0].detach().exp()+32).round().long().tolist()
            else:capacity=capacities
            n_count=max(self.minimum_nodes,min(self.nodes,int(capacity[0])));c_count=max(self.minimum_components,min(self.components,int(capacity[1])))
        gain,shift=self.condition(pooled).chunk(2,-1)
        nq=self.node_queries.weight[None,:n_count]*(1+gain[:,None].tanh())+shift[:,None]
        cq=self.component_queries.weight[None,:c_count]*(1+gain[:,None].tanh())+shift[:,None]
        memory=self.image(features)
        both=torch.cat((nq,cq),1)
        both=both+self.image_attention(both,memory,memory,need_weights=False)[0]
        nq,cq=both.split((n_count,c_count),1); nq=nq+self.node_mlp(nq)
        xy=self.node_grid[None,:n_count]+self.node_xy(nq)
        # Bipartite message passing: component queries read predicted node
        # features, then predict typed parameters and persistent node pointers.
        keys=self.ref_keys(nq)
        q=self.ref_queries(cq).reshape(b,c_count,MAX_REFS,-1)
        refs=torch.einsum('bcrd,bnd->bcrn',q,keys)/math.sqrt(keys.shape[-1])
        context=torch.einsum('bcn,bnd->bcd',refs[:,:,0].softmax(-1),nq)
        cq=cq+self.component_mlp(torch.cat((cq,context),-1))
        anchors=self.component_grid[None,:c_count,None]+self.anchor_xy(cq).reshape(b,c_count,MAX_REFS,2)
        q=self.ref_queries(cq).reshape(b,c_count,MAX_REFS,-1)
        refs=torch.einsum('bcrd,bnd->bcrn',q,keys)/math.sqrt(keys.shape[-1])
        refs=refs-400*((anchors[:,:,:,None]-xy.detach()[:,None,None]).square().sum(-1))
        aq=self.axis_query(nq).reshape(b,n_count,2,-1).transpose(1,2)
        ak=self.axis_key(nq).reshape(b,n_count,2,-1).transpose(1,2)
        axes=aq@ak.transpose(-1,-2)/math.sqrt(keys.shape[-1])
        axis_distance=(xy.detach()[:,:,None]-xy.detach()[:,None]).abs().permute(0,3,1,2)
        axes=axes-100*axis_distance
        return {'xy':xy,'anchors':anchors,'active':self.node_active(nq).squeeze(-1),
                'node_digits':self.node_digits(nq).reshape(b,n_count,2,self.coord_digits,10),'node_sign':self.node_sign(nq).reshape(b,n_count,2,2),
                'refs':refs,'kind':self.kind(cq),'params':self.params(cq),'role':self.role(cq),
                'digits':self.digits(cq).reshape(b,c_count,5,10),'text':self.text(cq),'template':self.template(cq),
                'bearing':self.bearing(cq),'size_digits':self.size_digits(cq).reshape(b,c_count,7,self.measure_digits,10),
                'size_sign':self.size_sign(cq).reshape(b,c_count,7,2),'log_count':log_count,
                'host':self.host_query(cq)@self.host_key(cq).transpose(-1,-2)/math.sqrt(keys.shape[-1]),
                'axis':axes}


@torch.no_grad()
def assignments(pred,target,batch=0):
    xy=pred['xy'][batch]; gt=target['nodes']
    if len(gt)>len(xy) or len(target['kind'])>len(pred['kind'][batch]):
        raise ValueError('Set capacity exceeded; never truncate required target')
    costs=torch.cdist(xy,gt,p=1)-.02*pred['active'][batch].sigmoid()[:,None]
    ni,nj=linear_sum_assignment(costs.cpu().numpy())
    inverse=torch.empty(len(gt),dtype=torch.long,device=xy.device); inverse[torch.as_tensor(nj,device=xy.device)]=torch.as_tensor(ni,device=xy.device)
    points=pred['anchors'][batch,:,0] if 'anchors' in pred else pred['refs'][batch,:,0].softmax(-1)@xy
    first=gt[target['refs'][:,0]]
    kinds=pred['kind'][batch].log_softmax(-1)
    cost=3*torch.cdist(points,first,p=1)-kinds[:,target['kind']]
    if 'anchors' in pred:
        reference_cost=torch.zeros_like(cost);reference_count=torch.zeros(len(first),device=xy.device)
        for slot in range(MAX_REFS):
            valid=target['refs'][:,slot]>=0
            if valid.any():
                reference_cost[:,valid]+=torch.cdist(pred['anchors'][batch,:,slot],gt[target['refs'][valid,slot]],p=1)
                reference_count[valid]+=1
        cost=3*reference_cost/reference_count.clamp_min(1)[None]-kinds[:,target['kind']]
    # Parameter matching applies only to defined parameters of the target type.
    mask=target['param_mask'].float()
    cost+=((pred['params'][batch,:,None]-target['params'][None]).abs()*mask[None]).sum(-1)/mask.sum(-1).clamp_min(1)[None]
    for name,weight in (('template',.5),('text',.2),('bearing',.25)):
        if name in pred and name in target:
            valid=target[name]>=0
            if valid.any():cost[:,valid]-=weight*pred[name][batch].log_softmax(-1)[:,target[name][valid]]
    ci,cj=linear_sum_assignment(cost.cpu().numpy())
    return inverse,torch.as_tensor(ci,device=xy.device),torch.as_tensor(cj,device=xy.device)


def loss(pred,targets,matches=None,*,term_weights=None,precision_digits=None):
    total=pred['xy'].sum()*0; details={}; all_matches=[]
    for b,t in enumerate(targets):
        match=matches[b] if matches is not None else assignments(pred,t,b); all_matches.append(match)
        inverse,ci,cj=match
        count_loss=F.mse_loss(pred['log_count'][b],pred['xy'].new_tensor([len(t['nodes']),len(t['kind'])]).log())
        active=torch.zeros_like(pred['active'][b]); active[inverse]=1
        dim_targets=t['kind']==0;dim_nodes=torch.unique(t['refs'][dim_targets].clamp_min(0))
        node_weights=pred['xy'].new_ones(len(t['nodes']));node_weights[dim_nodes]=10.
        node_loss=(F.smooth_l1_loss(pred['xy'][b,inverse],t['nodes'],beta=.0005,reduction='none').mean(-1)*node_weights).sum()/node_weights.sum()
        node_logits=pred['node_digits'][b,inverse];node_targets=t['node_digits']
        if precision_digits:
            keep=precision_digits[0]
            if torch.any(node_targets[...,:-keep]!=0):raise ValueError('Precision control would discard nonzero coordinate digits')
            node_logits=node_logits[...,-keep:,:];node_targets=node_targets[...,-keep:]
        node_precision=(F.cross_entropy(node_logits.reshape(-1,10),node_targets.reshape(-1))+
                        F.cross_entropy(pred['node_sign'][b,inverse].reshape(-1,2),t['node_sign'].reshape(-1)))
        node_obj=F.binary_cross_entropy_with_logits(pred['active'][b],active)
        cls=torch.full((pred['kind'].shape[1],),len(TYPES),device=ci.device,dtype=torch.long); cls[ci]=t['kind'][cj]
        weights=pred['kind'].new_ones(len(TYPES)+1); weights[-1]=.1; weights[0]=4
        type_loss=F.cross_entropy(pred['kind'][b],cls,weight=weights)
        refs=t['refs'][cj]; valid=refs>=0
        destination=inverse[refs.clamp_min(0)]
        reference_weights=pred['xy'].new_ones(refs.shape);reference_weights[t['kind'][cj]==0]=20.
        pointer_values=F.cross_entropy(pred['refs'][b,ci][valid],destination[valid],reduction='none')
        pointer=(pointer_values*reference_weights[valid]).sum()/reference_weights[valid].sum()
        proposal_values=F.smooth_l1_loss(pred['anchors'][b,ci][valid],t['nodes'][refs.clamp_min(0)][valid],beta=.0005,reduction='none').mean(-1)
        proposal=(proposal_values*reference_weights[valid]).sum()/reference_weights[valid].sum()
        pm=t['param_mask'][cj]
        parameter=F.smooth_l1_loss(pred['params'][b,ci][pm],t['params'][cj][pm],beta=.0005)
        roles=F.cross_entropy(pred['role'][b,ci],t['role'][cj])
        digits=t['digits'][cj]; dim=digits[:,0]>=0
        numeric=F.cross_entropy(pred['digits'][b,ci[dim]].reshape(-1,10),digits[dim].reshape(-1)) if dim.any() else parameter*0
        txt=t['text'][cj]; known=txt>=0
        text_loss=F.cross_entropy(pred['text'][b,ci[known]],txt[known]) if known.any() else parameter*0
        templ=t['template'][cj]; known_template=templ>=0
        template_loss=F.cross_entropy(pred['template'][b,ci[known_template]],templ[known_template]) if known_template.any() else parameter*0
        bearing=t['bearing'][cj];defined=bearing>=0
        bearing_loss=F.cross_entropy(pred['bearing'][b,ci[defined]],bearing[defined]) if defined.any() else parameter*0
        sd=t['size_digits'][cj];defined=sd[:,:,0]>=0
        size_logits=pred['size_digits'][b,ci][defined];size_targets=sd[defined]
        if precision_digits:
            keep=precision_digits[1]
            if torch.any(size_targets[...,:-keep]!=0):raise ValueError('Precision control would discard nonzero size digits')
            size_logits=size_logits[...,-keep:,:];size_targets=size_targets[...,-keep:]
        scalar_loss=(F.cross_entropy(size_logits.reshape(-1,10),size_targets.reshape(-1))+
                     F.cross_entropy(pred['size_sign'][b,ci][defined],t['size_sign'][cj][defined])) if defined.any() else parameter*0
        # Axis representatives are themselves matched predicted nodes. The
        # reference classes are not arbitrary per-file group-label numbers.
        axis_dest=inverse[t['axis']]
        axis=F.cross_entropy(pred['axis'][b,:,inverse].reshape(-1,pred['xy'].shape[1]),axis_dest.reshape(-1))
        comp_inverse=torch.empty(len(t['kind']),device=ci.device,dtype=torch.long); comp_inverse[cj]=ci
        host=t['host'][cj]; known_host=host>=0
        host_loss=F.cross_entropy(pred['host'][b,ci[known_host]],comp_inverse[host[known_host]]) if known_host.any() else parameter*0
        # Supervise the actual dimension reference geometry in millimetres.
        if dim.any():
            soft=pred['refs'][b,ci[dim],:2].softmax(-1)
            pts=soft@pred['xy'][b]*UNIT
            angle=t['params'][cj[dim],:2]; direction=torch.stack((angle[:,1],-angle[:,0]),-1)
            linear=t['params'][cj[dim],2]<.5
            length=torch.where(linear,((pts[:,1]-pts[:,0])*direction).sum(-1).abs(),(pts[:,1]-pts[:,0]).norm(dim=-1))
            value=(digits[dim]*digits.new_tensor([10000,1000,100,10,1])).sum(-1).float()
            dimension=F.smooth_l1_loss(length/UNIT,value/UNIT,beta=.0001)
        else: dimension=parameter*0
        value=100*node_loss+node_precision+40*proposal+node_obj+type_loss+pointer+20*parameter+roles*.2+numeric+text_loss*.3+template_loss+bearing_loss+scalar_loss+axis*.3+host_loss*.3+dimension*4+count_loss
        terms=dict(node=node_loss,node_precision=node_precision,proposal=proposal,node_objectness=node_obj,
                   type=type_loss,pointer=pointer,parameter=parameter,role=roles,numeric=numeric,
                   text=text_loss,template=template_loss,bearing=bearing_loss,scalar=scalar_loss,
                   axis=axis,host=host_loss,dimension=dimension,count=count_loss)
        default_weights=DEFAULT_LOSS_WEIGHTS
        for name,weight in (term_weights or {}).items():
            if name not in terms:raise ValueError('Unknown loss term: '+name)
            value=value+(weight-default_weights[name])*terms[name]
        total+=value/len(targets)
        for key,v in terms.items():
            details[key]=details.get(key,0)+float(v.detach())/len(targets)
    return total,details,all_matches


@torch.no_grad()
def decode(pred,texts,threshold=.5,batch=0,templates=None):
    xy=pred['xy'][batch].cpu().numpy()*UNIT
    probability=pred['node_digits'][batch].softmax(-1);digit_conf=probability.amax(-1).amin(-1).amin(-1)
    precise=(probability.argmax(-1)*probability.new_tensor([10**i for i in range(probability.shape[-2]-1,-1,-1)])).sum(-1).cpu().numpy()/10
    precise*=np.where(pred['node_sign'][batch].argmax(-1).cpu().numpy(),-1,1)
    sign_conf=pred['node_sign'][batch].softmax(-1).amax(-1).amin(-1)
    consistent=torch.from_numpy(np.abs(precise-xy).max(-1)<=10).to(digit_conf.device)
    mask=((digit_conf>.99)&(sign_conf>.99)&consistent).cpu().numpy();xy[mask]=precise[mask]
    probs=pred['kind'][batch].softmax(-1); conf,kind=probs.max(-1)
    reference_logits=pred['refs'][batch].clone()
    active=pred['active'][batch].sigmoid()>.5
    if int(active.sum())>=MAX_REFS:reference_logits[...,~active]=-float('inf')
    refs=reference_logits.argmax(-1).cpu().numpy(); params=pred['params'][batch].cpu().numpy()
    digits=pred['digits'][batch].argmax(-1).cpu().numpy(); text=pred['text'][batch].argmax(-1).cpu().numpy()
    roles=pred['role'][batch].argmax(-1).cpu().numpy(); host=pred['host'][batch].argmax(-1).cpu().numpy()
    library=templates or {}; template_keys=['<unknown>']+sorted(library); template_indices=pred['template'][batch].argmax(-1).cpu().numpy()
    bearing=pred['bearing'][batch].argmax(-1).cpu().numpy()
    sizes=(pred['size_digits'][batch].argmax(-1)*pred['size_digits'].new_tensor([10**i for i in range(pred['size_digits'].shape[-2]-1,-1,-1)])).sum(-1).cpu().numpy()
    sizes*=np.where(pred['size_sign'][batch].argmax(-1).cpu().numpy(),-1,1)
    components=[]; query_to_component={}; bad=0
    for i in range(len(kind)):
        k=int(kind[i]); score=float(conf[i])
        if k==len(TYPES) or score<threshold: continue
        name=TYPES[k]; length=3 if name=='dimension' else 2 if name in ('centerline','unresolved_edge','symbol') else 1
        if name=='native_path': length=int(np.clip(round(params[i,1]*MAX_REFS),2,MAX_REFS))
        ids=refs[i,:length].tolist()
        required=length if name=='native_path' else 2 if name in ('dimension','centerline','unresolved_edge','symbol') else 1
        used=set()
        for slot in range(required):
            if ids[slot] in used:
                candidates=reference_logits[i,slot].clone();candidates[list(used)]=-float('inf');ids[slot]=int(candidates.argmax())
            used.add(ids[slot])
        bad+=int(len(set(ids[:required]))!=required)
        query_to_component[i]=len(components)
        parameters=decode_component(name,params[i],digits[i],text[i],texts)
        if name=='native_symbol':parameters={'size_mm':max(1.,abs(float(params[i,0]))*UNIT),'template_id':template_keys[template_indices[i]]}
        if bearing[i]<4:
            key='angle_cad' if name=='dimension' else 'start_degrees' if name in ('swing_opening','circular_arc') else 'angle_degrees'
            if name in ('dimension','swing_opening','circular_arc','wall_face_pair','rectangular_loop'):parameters[key]=int(bearing[i])*90
        if name in ('swing_opening','circular_arc'):parameters['radius_mm']=max(1,int(abs(sizes[i,0])))
        elif name=='wall_face_pair':
            parameters['thickness_mm']=max(1,int(abs(sizes[i,0])));parameters['face_extents_mm']=sizes[i,1:5].reshape(2,2).tolist()
        elif name=='rectangular_loop':parameters.update(width_mm=max(1,int(abs(sizes[i,0]))),height_mm=max(1,int(abs(sizes[i,1]))))
        elif name=='native_symbol':parameters['size_mm']=max(1,int(abs(sizes[i,0])))
        components.append({'id':f'Q{i:04d}','kind':name,'nodes':ids,'parameters':parameters,
                           'roles':[int(roles[i])],'confidence':score,'host_query':int(host[i]),'members':[],
                           'semantic_status':'model-geometric-component;not-staff-confirmed'})
    for c in components:
        h=query_to_component.get(c.pop('host_query'),-1)
        c['host']=h if h>=0 and components[h]['kind']=='wall_face_pair' else -1
    axis=pred['axis'][batch].argmax(-1).cpu().numpy()
    used={node for c in components for node in c['nodes']}
    extent=max(10000.,float(np.abs(xy[list(used)]).max())*2.2) if used else 10000.
    axis_conf=pred['axis'][batch].softmax(-1).amax(-1).cpu().tolist()
    return {'schema':'img2dwg-shared-component/v2','frame':{'schema':'img2dwg-vector/v1','canvas':[512,512],'scale':extent/512,'units':'mm'},
            'nodes_mm':xy.tolist(),'components':components,'axis_links':axis.tolist(),
            'axis_confidence':axis_conf,
            'templates':library,
            'high_confidence_0_1mm_coordinate_nodes':int(mask.sum()),
            'source':'image-model-prediction','invalid_repeated_references':bad,'complete_business_semantics':False}
