"""Continual tiny reproduction: preserve five input responses, learn five more.

The base model and an input-feature subspace are frozen. CAD supervision is
used only by training/evaluation. Inference has no case ID or target retrieval.
"""
import argparse,copy,json,random,sys,time
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import load_file,save_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.train_retention_ablation import digest,make_model,measurement,write
from scripts.train_guard_balance import physical_diagnostics,quality_score
from img2dwg.graph_adapter import ProtectedGraphAdapter
from img2dwg.graph_decoder import loss
from img2dwg.graph_update import calibrate_balance,coordinate_snapshot,guarded_step
from img2dwg.structured import encode
from img2dwg.graph_evaluation import PROTOCOL

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--device',default='cuda');p.add_argument('--preflight-only',action='store_true')
    p.add_argument('--suite-minutes',type=float,default=65);p.add_argument('--trial-minutes',type=float,default=25);a=p.parse_args()
    torch.set_num_threads(6);torch.manual_seed(20261014);torch.backends.cuda.matmul.allow_tf32=False
    if a.device=='cuda' and not torch.cuda.is_available():raise ValueError('GPU required')
    if (a.output/'manifest.json').exists():raise FileExistsError('Preserve the previous run')
    rows=json.loads((a.data/'index.json').read_text());c=json.loads((a.data/'config.json').read_text());prep=json.loads((a.data/'preparation.json').read_text())
    if len(rows)!=10 or any(r['split']!='train' for r in rows) or prep['twenty_calibration_test_accessed']:raise ValueError('TRAIN10 only')
    if digest(a.data/'initializer.safetensors')!=prep['expanded_initializer_sha256']:raise ValueError('Base source changed')
    library=json.loads((a.data/'library.json').read_text(encoding='utf-8'));vocab={x:i for i,x in enumerate(c['texts'])};tv={k:i+1 for i,k in enumerate(sorted(library))}
    bank={};bundles={};graphs={};targets={}
    for r in rows:
        k=r['sample_id'];d=a.data/k
        for name,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256'),('features.pt','features_sha256')]:
            if digest(d/name)!=r[field]:raise ValueError('Input snapshot changed')
        bank[k]=torch.load(d/'features.pt',weights_only=True).to(a.device)
        bundles[k]=json.loads((d/'components.json').read_text(encoding='utf-8'));graphs[k]=json.loads((d/'target.json').read_text(encoding='utf-8'))
        targets[k]={n:torch.from_numpy(v).to(a.device) for n,v in encode(bundles[k],vocab,tv,c['coord_digits'],c['measure_digits']).items()}
    old=[r for r in rows if r['cohort']=='original'];new=[r for r in rows if r['cohort']=='additional']
    if len(old)!=5 or len(new)!=5:raise ValueError('Five original and five additional cases required')
    base=make_model(c,a.device);base.load_state_dict(load_file(str(a.data/'initializer.safetensors')))
    model=ProtectedGraphAdapter(base,[bank[r['sample_id']] for r in old],base_capacity=[959,726]).to(a.device)
    fixed=[1198,951];started=time.monotonic()
    config={**c,'adapter':{'type':'protected-feature-residual/v1','hidden':128,'nodes':1198,'components':951,
        'base_capacity':[959,726],'protected_rank':model.protected_rank,'zero_tolerance':model.zero_tolerance,
        'inference_count':'image-predicted-active-and-no-object;fixed-query-reserve;no-prefix-crop',
        'source_CAD_or_case_id_access':False}}
    write(a.output/'config.json',config)
    initial=measurement(model,rows,bank,bundles,graphs,c,library,a.output/'initial',save=True,fixed_capacity=fixed)
    write(a.output/'initial-evaluation.json',initial)
    norms={r['sample_id']:float(model.protected_features(bank[r['sample_id']]).norm()) for r in rows}
    write(a.output/'feature-projection.json',{'protected_rank':model.protected_rank,'residual_norms':norms,'uses_target_CAD':False})
    if initial['groups']['original']['passed_cases']!=5 or initial['groups']['original']['dimensions_correct_geometry_and_value']!=112:
        write(a.output/'preflight.json',{'status':'failed-original-retention','initial':initial['groups'],'training_executed':False})
        raise ValueError('Padding/projection must retain the verified original five before learning')
    if any(norms[r['sample_id']]<.001 for r in new):raise ValueError('New vision observations indistinguishable from protected span')
    if a.preflight_only:
        write(a.output/'preflight.json',{'status':'passed','initial':initial['groups'],'residual_norms':norms,'training_executed':False});return
    # Only cached frozen-model outputs, never targets; real evaluation always recomputes forward.
    cached={}
    with torch.no_grad():
        for r in rows:cached[r['sample_id']]=model.pad_base(base(bank[r['sample_id']],capacities=[959,726]))
    calibration=calibrate_balance(model,new,bank,targets,fixed,all_trainable=True);write(a.output/'loss-calibration.json',calibration)
    save_file({k:v.detach().cpu().contiguous() for k,v in model.state_dict().items()},str(a.output/'adapter-initializer.safetensors'))
    initializer=digest(a.output/'adapter-initializer.safetensors');initial_state={k:v.detach().clone() for k,v in model.state_dict().items()}
    comparisons=[{'name':'protected-plain','balance':False},{'name':'protected-balanced','balance':True}]
    write(a.output/'manifest.json',{'schema':'protected-adapter-ten/v1','cases':10,'base_model_sha256':prep['expanded_initializer_sha256'],
        'adapter_initializer_sha256':initializer,'protocol':PROTOCOL,'comparisons':comparisons,'base_frozen':True,
        'protected_source':'original TRAIN input features only;no CAD','optimizer':'Adam','learning_rate':.003,'clip':5.,
        'guard_original_step_mm':2.,'guard_original_total_mm':10.,'guard_new_step_mm':50.,
        'updates_train_only_new_five':True,'original_retention_evaluated_on_real_forward':True,
        'count_policy':'learned no-object/active count;full fixed query reserve in training and inference',
        'calibration_parameter_scope':'all adapter trainable parameters;not EXP048 shared-trunk norms',
        'quality_check_seconds':90,'stable_pass_checks':2,'trial_minutes':a.trial_minutes,'suite_minutes':a.suite_minutes,
        'full_training_executed':False,'Space_deployed':False,'twenty_used':False})
    completed=[]
    for v in comparisons:
        if time.monotonic()-started>a.suite_minutes*60:break
        model.load_state_dict(initial_state);params=[p for p in model.parameters() if p.requires_grad]
        optimizer=torch.optim.Adam(params,lr=.003);matches={};guards=[];history=[];epoch=0;updates=0;accepted=0;stable=0;plateau=0
        best=-1.;best_node=float('inf');start=time.monotonic();last_check=start;next_early=[1,8,32];stop='resource-cap;not-fit'
        folder=a.output/v['name'];folder.mkdir(parents=True,exist_ok=True);weights=calibration['term_weights'] if v['balance'] else {}
        @torch.no_grad()
        def capture():return {r['sample_id']:coordinate_snapshot(model(bank[r['sample_id']],cached_base=cached[r['sample_id']])) for r in rows}
        origin=capture();original_ids=[r['sample_id'] for r in old]
        history.append({'dose':0,'updates':0,'exposures':0,'groups':initial['groups'],'inferred_groups':initial['groups']})
        while time.monotonic()-start<a.trial_minutes*60 and time.monotonic()-started<a.suite_minutes*60:
            epoch+=1;order=new.copy();random.Random(20261014+epoch).shuffle(order);keys=[r['sample_id'] for r in order]
            features=torch.cat([bank[k] for k in keys]);cached_batch={key:torch.cat([cached[k][key] for k in keys]) for key in cached[keys[0]]}
            optimizer.zero_grad(set_to_none=True);pred=model(features,cached_base=cached_batch)
            known=[matches[k] for k in keys] if all(k in matches for k in keys) and epoch%20 else None
            value,details,found=loss(pred,[targets[k] for k in keys],known,term_weights=weights)
            if not torch.isfinite(value):raise ValueError('Nonfinite adapter loss')
            value.backward();norm=torch.nn.utils.clip_grad_norm_(params,5.)
            if not torch.isfinite(norm):raise ValueError('Nonfinite adapter gradient')
            guard=guarded_step(model,optimizer,capture,origin,original_ids,step_mm=2.,retention_mm=10.,additional_step_mm=50.)
            guards.append({'epoch':epoch,**guard});updates+=1;accepted+=int(guard['accepted'])
            for k,match in zip(keys,found):matches[k]=match
            check=(next_early and epoch>=next_early[0]) or time.monotonic()-last_check>=90
            if check:
                if next_early and epoch>=next_early[0]:next_early.pop(0)
                evaluated=measurement(model,rows,bank,bundles,graphs,c,library,folder/'temporary',fixed_capacity=fixed)
                physical=physical_diagnostics(model,rows,bank,targets,lambda r:fixed)
                score=quality_score(evaluated);node=float(np.mean([r['node_mean_mm'] for r in physical if r['cohort']=='additional']))
                plateau=0 if score>best+.002 or node<best_node-1. else plateau+1;best_node=min(best_node,node)
                if score>best:
                    best=score;save_file({k:x.detach().cpu().contiguous() for k,x in model.state_dict().items()},str(folder/'best.safetensors'))
                record={'dose':epoch,'updates':updates,'accepted_updates':accepted,'exposures':epoch*5,
                    'groups':evaluated['groups'],'inferred_groups':evaluated['groups'],'physical':physical,
                    'quality_score':score,'additional_node_mean_mm':node,'plateau_checks':plateau,'last_loss_terms':details,
                    'elapsed_seconds':time.monotonic()-start,'count_mode':'actual-image-selected-set;no GT capacity'}
                history.append(record);write(folder/'history.json',history);write(folder/'guard-history.json',guards)
                print(json.dumps({'variant':v['name'],**{k:record[k] for k in ['dose','updates','accepted_updates','groups','additional_node_mean_mm','plateau_checks','elapsed_seconds']}}),flush=True)
                if all(g['geometry_candidate_cases']==5 for g in evaluated['groups'].values()):
                    native=measurement(model,rows,bank,bundles,graphs,c,library,folder/f'quality-{epoch}',save=True,fixed_capacity=fixed)
                    stable=stable+1 if all(g['passed_cases']==5 for g in native['groups'].values()) else 0
                else:stable=0
                last_check=time.monotonic()
                if stable>=2:stop='stable-ten-actual-quality-pass';break
                if epoch>=128 and plateau>=8:stop='actual-structure-dimension-physical-plateau';break
        save_file({k:x.detach().cpu().contiguous() for k,x in model.state_dict().items()},str(folder/'model.safetensors'))
        final=measurement(model,rows,bank,bundles,graphs,c,library,folder/'fixed-final',save=True,fixed_capacity=fixed)
        inference=measurement(model,rows,bank,bundles,graphs,c,library,folder/'inferred-final',inferred=True,save=True,fixed_capacity=fixed)
        torch.save({'optimizer':optimizer.state_dict(),'matches':{k:tuple(t.cpu() for t in x) for k,x in matches.items()},'epoch':epoch},folder/'optimizer-and-assignment.pt')
        receipt={'status':'completed-diagnostic','variant':v,'stopping_reason':stop,'history':history,'updates':updates,'accepted_updates':accepted,
            'exposures':epoch*5,'initializer_sha256':initializer,'model_sha256':digest(folder/'model.safetensors'),
            'fixed_final':final,'inferred_final':inference,'loss_balance':calibration if v['balance'] else None,
            'guard_summary':{'attempts':len(guards),'accepted':accepted,'rejected':len(guards)-accepted,
                'mean_alpha':float(np.mean([g['alpha'] for g in guards])),'max_accepted_original_drift_mm':max((g['measured_original_drift_mm'] for g in guards if g['accepted']),default=None)},
            'frozen_base_sha256':prep['expanded_initializer_sha256'],'elapsed_seconds':time.monotonic()-start,
            'count_policy':'image-derived active/no-object;fixed reserve;no GT','full_training_executed':False,'Space_deployed':False}
        write(folder/'receipt.json',receipt);write(folder/'guard-history.json',guards);completed.append(receipt)
        print(json.dumps({'completed':v['name'],'fixed':final['groups'],'inferred':inference['groups'],'guard':receipt['guard_summary']}),flush=True)
    write(a.output/'receipt.json',{'status':'completed' if len(completed)==2 else 'partial-resource-cap','variants_planned':2,'variants_completed':len(completed),
        'conditions':completed,'training_cases':10,'new_five_adapter_updates':True,'full_training_executed':False,'Space_deployed':False,
        'elapsed_seconds':time.monotonic()-started,'twenty_used':False})
if __name__=='__main__':main()
