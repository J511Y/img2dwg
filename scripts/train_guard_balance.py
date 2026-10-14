"""Ten frozen TRAIN pairs: control, coordinate guard, loss balance, both.

No full trainer, held-out evaluator, model upload or Space deployment is called.
"""
import argparse,copy,json,random,sys,time
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import load_file,save_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.train_retention_ablation import digest,make_model,measurement,write
from img2dwg.graph_decoder import loss,assignments
from img2dwg.structured import encode,UNIT
from img2dwg.graph_update import calibrate_balance,coordinate_snapshot,guarded_step
from img2dwg.graph_evaluation import PROTOCOL

def variants():
    base={'lr':3e-5,'batch':'accumulate','order_seed':20261014,'refresh_every':20,
          'coordinate_guard':False,'gradient_balance':False,'step_mm':2.,'retention_mm':10.}
    return [{**base,'name':'control'},{**base,'name':'coordinate-guard','coordinate_guard':True},
            {**base,'name':'loss-balance','gradient_balance':True},
            {**base,'name':'guard-and-balance','coordinate_guard':True,'gradient_balance':True}]

def quality_score(result):
    groups=result['groups'];scores=[]
    for name in ('original','additional'):
        g=groups[name];dim=g['dimensions_correct_geometry_and_value']/g['required_dimensions']
        scores.append((min(g['structure_f1'],g['component_f1'],g['shared_reference_f1'])+dim)/2)
    return min(scores)+.1*sum(scores)/2

@torch.no_grad()
def physical_diagnostics(model,rows,bank,targets,capacity):
    result=[];model.eval()
    for r in rows:
        k=r['sample_id'];p=model(bank[k],capacities=capacity(r));inverse,ci,cj=assignments(p,targets[k])
        errors=(p['xy'][0,inverse]-targets[k]['nodes']).norm(dim=-1)*UNIT
        result.append({'sample_id':k,'cohort':r['cohort'],'node_mean_mm':float(errors.mean()),
            'node_p90_mm':float(torch.quantile(errors,.9)),'node_within_10mm':int((errors<=10).sum()),
            'required_nodes':len(errors),'component_type_matched_accuracy':float((p['kind'][0,ci].argmax(-1)==targets[k]['kind'][cj]).float().mean())})
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--device',default='cuda');p.add_argument('--suite-minutes',type=float,default=50)
    p.add_argument('--trial-minutes',type=float,default=10);p.add_argument('--preflight-only',action='store_true')
    a=p.parse_args();torch.set_num_threads(6);torch.manual_seed(20261014);torch.backends.cuda.matmul.allow_tf32=False
    if a.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('GPU required')
    if a.output.exists() and (a.output/'manifest.json').exists():raise FileExistsError('Preserve previous run')
    rows=json.loads((a.data/'index.json').read_text());c=json.loads((a.data/'config.json').read_text())
    prep=json.loads((a.data/'preparation.json').read_text());library=json.loads((a.data/'library.json').read_text(encoding='utf-8'))
    if len(rows)!=10 or sum(r['cohort']=='original' for r in rows)!=5 or any(r['split']!='train' for r in rows) or prep['twenty_calibration_test_accessed']:
        raise ValueError('Only the frozen five plus five TRAIN diagnostic is allowed')
    if digest(a.data/'initializer.safetensors')!=prep['expanded_initializer_sha256']:raise ValueError('Initializer changed')
    bank={};targets={};bundles={};graphs={};vocab={x:i for i,x in enumerate(c['texts'])};tv={k:i+1 for i,k in enumerate(sorted(library))}
    for r in rows:
        k=r['sample_id'];folder=a.data/k
        for name,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256'),('features.pt','features_sha256')]:
            if digest(folder/name)!=r[field]:raise ValueError('Frozen data changed: '+name)
        bank[k]=torch.load(folder/'features.pt',weights_only=True).to(a.device)
        bundles[k]=json.loads((folder/'components.json').read_text(encoding='utf-8'));graphs[k]=json.loads((folder/'target.json').read_text(encoding='utf-8'))
        targets[k]={name:torch.from_numpy(value).to(a.device) for name,value in encode(bundles[k],vocab,tv,c['coord_digits'],c['measure_digits']).items()}
    capacity=lambda r:[959,726] if r['cohort']=='original' else c['diagnostic_fixed_capacity']
    for r in rows:
        cap=capacity(r)
        if r['nodes']>cap[0] or r['component_count']>cap[1]:raise ValueError('Never truncate GT')
    initial=load_file(str(a.data/'initializer.safetensors'));model=make_model(c,a.device);model.load_state_dict(initial)
    started=time.monotonic();initial_eval=measurement(model,rows,bank,bundles,graphs,c,library,a.output/'initial',save=True)
    write(a.output/'initial-evaluation.json',initial_eval)
    old=initial_eval['groups']['original']
    if old['structure_f1']<.98 or old['dimensions_correct_geometry_and_value']!=112:raise ValueError('Initial reproduction changed')
    calibration=calibrate_balance(model,rows,bank,targets,capacity);write(a.output/'loss-calibration.json',calibration)
    print(json.dumps({'calibration':calibration}),flush=True)
    if a.preflight_only:
        write(a.output/'preflight.json',{'status':'passed','initial':initial_eval['groups'],'calibration':calibration,'training_executed':False});return
    manifest={'schema':'guard-balance-ten/v1','cases':10,'data_index_sha256':digest(a.data/'index.json'),
        'initializer_sha256':prep['expanded_initializer_sha256'],'feature_protocol':prep['feature_input'],
        'comparisons':variants(),'protocol':PROTOCOL,'train_capacity':'cohort-fixed;original959/726;additional1198/951',
        'same_Adam_restart':True,'global_clip':5.,'evaluation':'fixed and image-count, every32 exposures; early doses1/2/4/8/16',
        'quality_stop':'two consecutive all-ten geometry+nativeDXF+image-count pass checks',
        'plateau_stop':'five checks without physical node or real structure/dimension progress, after128 exposures',
        'maximum_exposure_safety_ceiling':2048,'ceiling_is_not_fit':True,'suite_minutes':a.suite_minutes,
        'trial_minutes':a.trial_minutes,'full_training_allowed':False,'Space_deployment_allowed':False,'twenty_used':False}
    write(a.output/'manifest.json',manifest);completed=[]
    original_ids=[r['sample_id'] for r in rows if r['cohort']=='original']
    for v in variants():
        if time.monotonic()-started>=a.suite_minutes*60:break
        model.load_state_dict(initial);optimizer=torch.optim.Adam(model.parameters(),lr=v['lr']);folder=a.output/v['name'];folder.mkdir(parents=True,exist_ok=True)
        weights=calibration['term_weights'] if v['gradient_balance'] else {};matches={};history=[];guard_log=[]
        updates=0;accepted=0;exposures=0;stable=0;plateau=0;best_score=-1.;best_node=float('inf');trial_start=time.monotonic()
        @torch.no_grad()
        def capture():
            model.eval();return {r['sample_id']:coordinate_snapshot(model(bank[r['sample_id']],capacities=capacity(r))) for r in rows}
        origin=capture() if v['coordinate_guard'] else None
        history.append({'dose':0,'updates':0,'exposures':0,'groups':initial_eval['groups'],'inferred_groups':None})
        stop='resource-cap;not-fit';last_epoch=0
        for epoch in range(1,2049):
            last_epoch=epoch;order=list(rows);random.Random(v['order_seed']+epoch).shuffle(order)
            for batch in [order[i:i+5] for i in range(0,len(order),5)]:
                model.train();optimizer.zero_grad(set_to_none=True)
                for r in batch:
                    k=r['sample_id'];pred=model(bank[k],capacities=capacity(r));cache=[matches[k]] if k in matches and epoch%v['refresh_every'] else None
                    value,details,found=loss(pred,[targets[k]],cache,term_weights=weights)
                    if not torch.isfinite(value):raise ValueError('Nonfinite loss')
                    (value/len(batch)).backward();matches[k]=found[0];exposures+=1
                norm=torch.nn.utils.clip_grad_norm_(model.parameters(),5.)
                if not torch.isfinite(norm):raise ValueError('Nonfinite gradient')
                if v['coordinate_guard']:
                    guard=guarded_step(model,optimizer,capture,origin,original_ids,step_mm=v['step_mm'],retention_mm=v['retention_mm'])
                    guard_log.append({'attempt':updates+1,'epoch':epoch,**guard});accepted+=int(guard['accepted'])
                else:optimizer.step();accepted+=1
                updates+=1
                if time.monotonic()-trial_start>=a.trial_minutes*60 or time.monotonic()-started>=a.suite_minutes*60:break
            check=epoch in (1,2,4,8,16) or epoch%32==0 or time.monotonic()-trial_start>=a.trial_minutes*60 or time.monotonic()-started>=a.suite_minutes*60
            if check:
                fixed=measurement(model,rows,bank,bundles,graphs,c,library,folder/'temporary')
                inferred=measurement(model,rows,bank,bundles,graphs,c,library,folder/'temporary-image-count',inferred=True)
                physical=physical_diagnostics(model,rows,bank,targets,capacity)
                node=float(np.mean([r['node_mean_mm'] for r in physical if r['cohort']=='additional']))
                score=quality_score(fixed);improved=score>best_score+.002 or node<best_node-1.
                plateau=0 if improved else plateau+1;best_node=min(best_node,node)
                if score>best_score:
                    best_score=score;save_file({k:t.detach().cpu().contiguous() for k,t in model.state_dict().items()},str(folder/'best.safetensors'))
                row={'dose':epoch,'updates':updates,'accepted_updates':accepted,'exposures':exposures,'groups':fixed['groups'],
                     'inferred_groups':inferred['groups'],'physical':physical,'last_loss_terms':details,'quality_score':score,
                     'additional_node_mean_mm':node,'plateau_checks':plateau,'elapsed_seconds':time.monotonic()-trial_start}
                history.append(row);write(folder/'history.json',history);write(folder/'guard-history.json',guard_log)
                print(json.dumps({'variant':v['name'],**{k:row[k] for k in ['dose','updates','accepted_updates','groups','inferred_groups','additional_node_mean_mm','plateau_checks','elapsed_seconds']}}),flush=True)
                candidates=all(g['geometry_candidate_cases']==g['cases'] for g in fixed['groups'].values()) and all(g['geometry_candidate_cases']==g['cases'] for g in inferred['groups'].values())
                if candidates:
                    native=measurement(model,rows,bank,bundles,graphs,c,library,folder/f'quality-check-{epoch}',inferred=True,save=True)
                    stable=stable+1 if all(g['passed_cases']==g['cases'] for g in native['groups'].values()) else 0
                else:stable=0
                if stable>=2:stop='stable-ten-quality-pass';break
                if epoch>=128 and plateau>=5:stop='structure-dimension-and-physical-plateau';break
            if time.monotonic()-trial_start>=a.trial_minutes*60:stop='trial-resource-cap;not-fit';break
            if time.monotonic()-started>=a.suite_minutes*60:stop='suite-resource-cap;not-fit';break
        else:stop='exposure-safety-ceiling;not-fit'
        save_file({k:t.detach().cpu().contiguous() for k,t in model.state_dict().items()},str(folder/'model.safetensors'))
        final=measurement(model,rows,bank,bundles,graphs,c,library,folder/'fixed-final',save=True)
        inferred_final=measurement(model,rows,bank,bundles,graphs,c,library,folder/'inferred-final',inferred=True,save=True)
        # Final weights are the primary comparison; retain, but never substitute, best-score weights.
        torch.save({'model_sha256':digest(folder/'model.safetensors'),'optimizer':optimizer.state_dict(),
                    'matches':{k:tuple(t.cpu() for t in value) for k,value in matches.items()},'epoch':last_epoch,'updates':updates},folder/'optimizer-and-assignment.pt')
        receipt={'status':'completed-diagnostic','variant':v,'history':history,'stopping_reason':stop,'updates':updates,'accepted_updates':accepted,
                 'exposures':exposures,'final_dose':last_epoch,'initializer_sha256':prep['expanded_initializer_sha256'],
                 'model_sha256':digest(folder/'model.safetensors'),'best_model_sha256':digest(folder/'best.safetensors'),
                 'fixed_final':final,'inferred_final':inferred_final,'loss_balance':calibration if v['gradient_balance'] else None,
                 'guard_summary':{'attempts':len(guard_log),'accepted':sum(x['accepted'] for x in guard_log),
                    'rejected':sum(not x['accepted'] for x in guard_log),'mean_alpha':float(np.mean([x['alpha'] for x in guard_log])) if guard_log else None,
                    'max_accepted_step_mm':max((x['measured_step_mm'] for x in guard_log if x['accepted']),default=None),
                    'max_accepted_original_drift_mm':max((x['measured_original_drift_mm'] for x in guard_log if x['accepted']),default=None)},
                 'elapsed_seconds':time.monotonic()-trial_start,'full_training_executed':False,'Space_deployed':False}
        write(folder/'receipt.json',receipt);write(folder/'guard-history.json',guard_log);completed.append(receipt)
        print(json.dumps({'completed':v['name'],'fixed':final['groups'],'inferred':inferred_final['groups'],'guard':receipt['guard_summary']}),flush=True)
        write(a.output/'progress.json',{'completed':[r['variant']['name'] for r in completed],'elapsed_seconds':time.monotonic()-started})
    write(a.output/'receipt.json',{'status':'completed' if len(completed)==4 else 'partial-resource-cap','variants_planned':4,
         'variants_completed':len(completed),'conditions':completed,'elapsed_seconds':time.monotonic()-started,
         'training_cases':10,'twenty_used':False,'full_training_executed':False,'Space_deployed':False})
if __name__=='__main__':main()
