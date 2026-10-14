"""TRAIN-only physical output trust region and one-time group gradient balance.

No target CAD is read by the trust region. Query movement is measured in mm,
including the numeric-coordinate substitution used by the real decoder.
This does not certify changed topology, symbols, or post-solver geometry.
"""
import copy,math
import torch
from img2dwg.graph_decoder import DEFAULT_LOSS_WEIGHTS,loss
from img2dwg.structured import UNIT

CONTINUOUS_TERMS=('node','proposal','parameter','dimension')

@torch.no_grad()
def coordinate_snapshot(pred):
    xy=pred['xy']*UNIT
    probability=pred['node_digits'].softmax(-1)
    powers=probability.new_tensor([10**i for i in range(probability.shape[-2]-1,-1,-1)])
    precise=(probability.argmax(-1)*powers).sum(-1)/10
    precise*=torch.where(pred['node_sign'].argmax(-1).bool(),-1.,1.)
    confident=(probability.amax(-1).amin(-1).amin(-1)>.99)&(pred['node_sign'].softmax(-1).amax(-1).amin(-1)>.99)
    use=confident&((precise-xy).abs().amax(-1)<=10)
    return {'xy_mm':xy.detach().clone(),'anchors_mm':(pred['anchors']*UNIT).detach().clone(),
            'decoded_nodes_mm':torch.where(use[...,None],precise,xy).detach().clone()}

def maximum_movement(before,after):
    if before.keys()!=after.keys():raise ValueError('Guard cohort changed')
    result=0.
    for key,old in before.items():
        for field,value in old.items():
            new=after[key][field]
            if value.shape!=new.shape:raise ValueError('Guard capacity changed')
            if not torch.isfinite(new).all():return math.inf
            result=max(result,float((new-value).norm(dim=-1).max()))
    return result

def balanced_weights(continuous_norm,categorical_norm,minimum=.01):
    if not math.isfinite(continuous_norm+categorical_norm) or min(continuous_norm,categorical_norm)<0:
        raise ValueError('Invalid calibration gradient')
    continuous_scale=max(minimum,min(1.,categorical_norm/max(continuous_norm,1e-12)))
    categorical_scale=max(minimum,min(1.,continuous_norm/max(categorical_norm,1e-12)))
    weights={k:v*(continuous_scale if k in CONTINUOUS_TERMS else categorical_scale) for k,v in DEFAULT_LOSS_WEIGHTS.items()}
    return weights,continuous_scale,categorical_scale

def calibrate_balance(model,rows,bank,targets,capacity):
    """Freeze a scale from mean gradients on the same ten TRAIN observations.

    The larger group is downweighted, keeping each group's internal weight ratio.
    The shared feature/MLP trunk, not head size, defines gradient balance.
"""
    model.eval();named=[(k,p) for k,p in model.named_parameters() if k.startswith(('image.','condition.','image_attention.','node_mlp.','component_mlp.'))]
    params=[p for _,p in named];cg=[torch.zeros_like(p) for p in params];dg=[torch.zeros_like(p) for p in params]
    categorical_zero={k:0. for k in DEFAULT_LOSS_WEIGHTS if k not in CONTINUOUS_TERMS}
    for r in rows:
        key=r['sample_id'];pred=model(bank[key],capacities=capacity(r) if callable(capacity) else capacity)
        full,_,matches=loss(pred,[targets[key]])
        geometry,_,_=loss(pred,[targets[key]],matches,term_weights=categorical_zero)
        continuous=torch.autograd.grad(geometry,params,retain_graph=True,allow_unused=True)
        discrete=torch.autograd.grad(full-geometry,params,allow_unused=True)
        for dest,grads in [(cg,continuous),(dg,discrete)]:
            for d,g in zip(dest,grads):
                if g is not None:d.add_(g.detach()/len(rows))
    cn=float(torch.sqrt(sum(g.square().sum() for g in cg)));dn=float(torch.sqrt(sum(g.square().sum() for g in dg)))
    weights,continuous_scale,categorical_scale=balanced_weights(cn,dn)
    return {'schema':'group-gradient-balance/v1','continuous_terms':CONTINUOUS_TERMS,
            'continuous_shared_gradient_L2':cn,'categorical_shared_gradient_L2':dn,
            'continuous_scale':continuous_scale,'categorical_scale':categorical_scale,'term_weights':weights,'calibration_cases':len(rows),
            'calibration_updates':0,'frozen_after_initialization':True,
            'shared_parameters':[k for k,_ in named],'minimum_scale':.01,'within_group_weight_ratios_unchanged':True}

def guarded_step(model,optimizer,capture,origin,original_ids,*,step_mm=2.,retention_mm=10.,backtracks=8):
    """Scale the proposed Adam parameter delta until measured outputs are safe.

Accepted scaled updates keep the proposed Adam moments. Rejected updates
restore both weights and optimizer state; no rejected attempt becomes progress.
"""
    before=capture();parameters=list(model.parameters());old=[p.detach().clone() for p in parameters]
    state=copy.deepcopy(optimizer.state_dict());optimizer.step()
    delta=[p.detach()-q for p,q in zip(parameters,old)]
    accepted=False;step=math.inf;retention=math.inf;alpha=0.
    for trial in range(backtracks+1):
        alpha=2.**(-trial)
        with torch.no_grad():
            for p,q,d in zip(parameters,old,delta):p.copy_(q+alpha*d)
        after=capture();step=maximum_movement(before,after)
        retention=maximum_movement({k:origin[k] for k in original_ids},{k:after[k] for k in original_ids})
        if step<=step_mm and retention<=retention_mm:accepted=True;break
    if not accepted:
        with torch.no_grad():
            for p,q in zip(parameters,old):p.copy_(q)
        optimizer.load_state_dict(state);alpha=0.
    return {'accepted':accepted,'alpha':alpha,'backtracks':trial,'proposed_trials':trial+1,
            'measured_step_mm':step if math.isfinite(step) else None,
            'measured_original_drift_mm':retention if math.isfinite(retention) else None,
            'step_limit_mm':step_mm,'original_total_limit_mm':retention_mm,
            'optimizer_restored_on_rejection':not accepted}
