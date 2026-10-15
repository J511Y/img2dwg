"""Small TRAIN-only, matched-exposure interventions. Never launches full training or deploys."""
import argparse,copy,hashlib,json,random,sys,time
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import load_file,save_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.graph_decoder import SharedGraphDecoder,decode,loss
from img2dwg.structured import encode,compile_graph
from img2dwg.graph_constraints import project
from img2dwg.graph_evaluation import evaluate,PROTOCOL
from img2dwg.raw_evaluation import aggregate
from img2dwg.vector import exports,svg

DOSES=(0,1,2,4,8,16,32)
def variants():
    base={'batch':'accumulate','capacity':'fixed','loss_weights':{},'precision_digits':None,
          'lr':.0001,'refresh_every':20,'order_seed':20261014}
    result=[]
    def add(name,cohort,**changes):result.append({**copy.deepcopy(base),'name':name,'cohort':cohort,**changes})
    add('five-joint','five',batch='joint')
    add('five-online','five',batch='online')
    add('five-accumulate','five')
    add('five-legacy-digit-loss','five',precision_digits=(6,5))
    add('five-lower-lr','five',lr=.00003)
    add('mixed-joint','mixed',batch='joint')
    add('mixed-online','mixed',batch='online')
    add('mixed-accumulate','mixed')
    add('mixed-variable-capacity','mixed',capacity='variable')
    add('mixed-count-loss-off','mixed',capacity='variable',loss_weights={'count':0})
    add('mixed-legacy-digit-loss','mixed',capacity='variable',precision_digits=(6,5))
    add('mixed-template-loss-off','mixed',capacity='variable',loss_weights={'template':0})
    add('mixed-lower-lr','mixed',capacity='variable',lr=.00003)
    add('mixed-refresh-assignment','mixed',capacity='variable',refresh_every=1)
    add('five-online-order2','five',batch='online',order_seed=20261015)
    add('five-accumulate-order2','five',order_seed=20261015)
    return result

def write(path,data):Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def make_model(c,device):
    return SharedGraphDecoder(c['nodes'],c['components'],len(c['texts']),hidden=c['hidden'],templates=c['templates'],
         coord_digits=c['coord_digits'],measure_digits=c['measure_digits'],adaptive_capacity=True,
         minimum_nodes=c['minimum_nodes'],minimum_components=c['minimum_components']).to(device)

def candidate_pass(m):
    d=m['components']['dimension'];symbols=m['components']['symbol'];res=m.get('constraint_receipt',{}).get('max_residual_mm')
    return bool(m['structure_f1']>=.9 and m['component_f1']>=.95 and m['shared_reference_f1']>=.95 and
        d['missing_or_incorrect']==0 and d['extra_predicted']==0 and symbols['matched']==symbols['target'] and
        m['native_dimension_supervision_missing']==0 and m['host_recall']==1 and
        m['invalid_repeated_node_references']==0 and m['unsupported_components']==0 and (res is None or res<=1))

@torch.no_grad()
def compact_bundle(bundle):
    """Retain every used prototype, without duplicating the unused catalog."""
    used={c['parameters']['template_id'] for c in bundle['components'] if c['kind']=='native_symbol'}
    return {**bundle,'templates':{k:v for k,v in bundle.get('templates',{}).items() if k in used},
            'artifact_template_catalog_total':len(bundle.get('templates',{}))}

@torch.no_grad()
def measurement(model,rows,bank,bundles,graphs,config,library,out,*,inferred=False,save=False,fixed_capacity=None,reference_radius_mm=None,set_selection='no-object',dimension_consistency_mm=None,projection_limit_mm=None,compact_artifacts=False):
    model.eval();result=[]
    for r in rows:
        key=r['sample_id'];cap=None if inferred else (fixed_capacity or ([959,726] if r['cohort']=='original' else config['diagnostic_fixed_capacity']))
        pred=model(bank[key],capacities=cap);raw=decode(pred,config['texts'],templates=library,reference_radius_mm=reference_radius_mm,set_selection=set_selection,dimension_consistency_mm=dimension_consistency_mm);solved=project(raw,maximum_displacement_mm=projection_limit_mm)
        folder=out/key;error=None;factory=None
        try:
            graph=compile_graph(solved,strict=False)
            if save:
                stored={**graph,'shared_component_graph':compact_bundle(solved)} if compact_artifacts else graph
                factory=exports(stored,folder)
        except Exception as exc:
            error=type(exc).__name__+': '+str(exc);graph={**solved['frame'],'components':[],'texts':[],'unsupported_components':['compile-error']}
        m=evaluate(solved,bundles[key],graph,graphs[key],factory)
        m['reference_resolution_receipt']=raw['reference_resolution_receipt']
        m['query_selection_receipt']=raw['query_selection_receipt']
        selection_invalid=raw['reference_resolution_receipt']['unresolved_slots'] or raw['query_selection_receipt'].get('capacity_limited',False) or solved.get('constraint_receipt',{}).get('status')=='rejected-displacement'
        if selection_invalid:m['passed']=False
        m.update(sample_id=key,cohort=r['cohort'],geometry_candidate_without_DXF_audit=candidate_pass(m),
                 actual_DXF_audit_executed=bool(factory is not None),capacity_nodes=pred['xy'].shape[1],capacity_components=pred['kind'].shape[1],
                 capacity_below_required=bool(pred['xy'].shape[1]<r['nodes'] or pred['kind'].shape[1]<r['component_count']),
                 export_error=error)
        if selection_invalid:m['geometry_candidate_without_DXF_audit']=False
        try:raw_graph=compile_graph(raw,strict=False)
        except Exception as exc:
            raw_graph={**raw['frame'],'components':[],'texts':[],'unsupported_components':['raw-compile-error']}
            m['raw_compile_error']=type(exc).__name__+': '+str(exc);m['passed']=False
            m['geometry_candidate_without_DXF_audit']=False
        before=evaluate(raw,bundles[key],raw_graph,graphs[key],None)
        m['before_constraints']={k:before[k] for k in ['structure_f1','component_f1','shared_reference_f1']}
        m['before_constraints']['dimension']=before['components']['dimension']
        result.append(m)
        if save:
            write(folder/'metrics.json',m);write(folder/'shared-graph.json',compact_bundle(solved) if compact_artifacts else solved)
            (folder/'raw.svg').write_text(svg(raw_graph),encoding='utf-8')
    groups={}
    for group in ['original','additional']:
        rr=[m for m in result if m['cohort']==group]
        if not rr:continue
        agg=aggregate(rr)
        agg.update(geometry_candidate_cases=sum(m['geometry_candidate_without_DXF_audit'] for m in rr),
                   actual_DXF_audit_executed=save,capacity_below_required_cases=sum(m['capacity_below_required'] for m in rr),
                   component_f1=float(np.mean([m['component_f1'] for m in rr])),
                   shared_reference_f1=float(np.mean([m['shared_reference_f1'] for m in rr])))
        groups[group]=agg
    mode='image-active-no-object-selection;fixed-query-reserve' if hasattr(model,'protected_features') else ('image-predicted' if inferred else 'fixed-diagnostic-prefix')
    return {'groups':groups,'rows':result,'capacity_mode':mode}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--device',default='cuda');parser.add_argument('--suite-minutes',type=float,default=65)
    parser.add_argument('--trial-minutes',type=float,default=4);parser.add_argument('--preflight-only',action='store_true')
    parser.add_argument('--comparison-plan',type=Path);a=parser.parse_args()
    torch.set_num_threads(6);torch.manual_seed(20261014);torch.backends.cuda.matmul.allow_tf32=False
    if a.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('GPU is required for matched training comparisons')
    rows=json.loads((a.data/'index.json').read_text());c=json.loads((a.data/'config.json').read_text())
    library=json.loads((a.data/'library.json').read_text(encoding='utf-8'));prep=json.loads((a.data/'preparation.json').read_text())
    if len(rows)!=10 or any(r['split']!='train' for r in rows):raise ValueError('Diagnostic refuses non-TRAIN or >10-case input')
    if prep['twenty_calibration_test_accessed']:raise ValueError('Evaluation cohorts must remain unopened')
    if digest(a.data/'initializer.safetensors')!=prep['expanded_initializer_sha256']:raise ValueError('Initializer changed')
    bank={};targets={};bundles={};graphs={};vocab={text:i for i,text in enumerate(c['texts'])};tv={key:i+1 for i,key in enumerate(sorted(library))}
    for r in rows:
        key=r['sample_id'];folder=a.data/key
        for name,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256'),('features.pt','features_sha256')]:
            if digest(folder/name)!=r[field]:raise ValueError('Dataset artifact changed')
        bank[key]=torch.load(folder/'features.pt',weights_only=True).to(a.device)
        bundles[key]=json.loads((folder/'components.json').read_text(encoding='utf-8'));graphs[key]=json.loads((folder/'target.json').read_text(encoding='utf-8'))
        targets[key]={k:torch.from_numpy(v).to(a.device) for k,v in encode(bundles[key],vocab,tv,c['coord_digits'],c['measure_digits']).items()}
    initial=load_file(str(a.data/'initializer.safetensors'));model=make_model(c,a.device);model.load_state_dict(initial)
    started=time.monotonic();initial_eval=measurement(model,rows,bank,bundles,graphs,c,library,a.output/'initial',save=True)
    write(a.output/'initial-evaluation.json',initial_eval)
    old=initial_eval['groups']['original']
    if old['dimensions_correct_geometry_and_value']!=112 or old['structure_f1']<.98:
        raise ValueError('Original reproduction preflight changed; refuse learning before investigation')
    if a.preflight_only:
        write(a.output/'preflight.json',{'status':'passed','initial':initial_eval['groups'],'training_executed':False});return
    comparisons=json.loads(a.comparison_plan.read_text()) if a.comparison_plan else variants()
    if not comparisons or len(comparisons)>16:raise ValueError('Bounded comparison plan required')
    fields=set(variants()[0])
    for v in comparisons:
        if set(v)!=fields or v['cohort'] not in ('five','mixed') or v['batch'] not in ('joint','online','accumulate') or v['capacity'] not in ('fixed','variable'):
            raise ValueError('Unsupported intervention')
        if v['precision_digits'] not in (None,[6,5],(6,5)) or not 0<v['lr']<=.0001:
            raise ValueError('Numeric precision/rate outside diagnostic bounds')
        if v['batch']=='joint' and v['capacity']=='variable':raise ValueError('Use accumulation for variable capacities')
    manifest={'schema':'img2dwg-retention-ablation/v1','cases':10,'original_ids':[r['sample_id'] for r in rows if r['cohort']=='original'],
        'additional_ids':[r['sample_id'] for r in rows if r['cohort']=='additional'],'initializer_sha256':prep['expanded_initializer_sha256'],
        'source_checkpoint_sha256':prep['source_checkpoint']['source_sha256'],'feature_protocol':prep['feature_input'],
        'protocol':PROTOCOL,'comparisons':comparisons,'diagnostic_exposure_doses':DOSES,
        'dose_is_not_fit_or_convergence':True,'new_optimizer_each_variant':True,'optimizer':'Adam',
        'global_gradient_clip_norm':5,'suite_cap_minutes':a.suite_minutes,'trial_cap_minutes':a.trial_minutes,
        'full_training_or_deployment_allowed':False,'twenty_used':False}
    write(a.output/'manifest.json',manifest);completed=[]
    for variant in comparisons:
        if time.monotonic()-started>a.suite_minutes*60:break
        folder=a.output/variant['name'];folder.mkdir(parents=True,exist_ok=True)
        model.load_state_dict(initial);optimizer=torch.optim.Adam(model.parameters(),lr=variant['lr'])
        matches={};history=[];updates=0;exposures=0;trial_start=time.monotonic()
        subset=rows[:5] if variant['cohort']=='five' else rows
        common=[959,726] if variant['cohort']=='five' else c['diagnostic_fixed_capacity']
        zero_groups={k:v for k,v in initial_eval['groups'].items() if k=='original' or variant['cohort']=='mixed'}
        history.append({'dose':0,'updates':0,'exposures':0,'groups':zero_groups})
        stop='diagnostic-dose-cap;not-fit';last_details={};step_log=[]
        for epoch in range(1,DOSES[-1]+1):
            order=list(subset);random.Random(variant['order_seed']+epoch).shuffle(order)
            batches=[[r] for r in order] if variant['batch']=='online' else [order[i:i+5] for i in range(0,len(order),5)]
            for batch in batches:
                model.train();optimizer.zero_grad(set_to_none=True)
                microbatches=[batch] if variant['batch']=='joint' else [[r] for r in batch]
                for micro in microbatches:
                    keys=[r['sample_id'] for r in micro]
                    cap=[max(959,micro[0]['nodes']+32),max(726,micro[0]['component_count']+32)] if variant['capacity']=='variable' else common
                    pred=model(torch.cat([bank[key] for key in keys]),capacities=cap)
                    cached=[matches[key] for key in keys] if all(key in matches for key in keys) and epoch%variant['refresh_every'] else None
                    value,details,found=loss(pred,[targets[key] for key in keys],cached,
                                            term_weights=variant['loss_weights'],precision_digits=variant['precision_digits'])
                    if not torch.isfinite(value):raise ValueError('Nonfinite loss')
                    (value*len(micro)/len(batch)).backward()
                    for key,match in zip(keys,found):matches[key]=match
                    last_details=details;exposures+=len(micro)
                norm=torch.nn.utils.clip_grad_norm_(model.parameters(),5.)
                if not torch.isfinite(norm):raise ValueError('Nonfinite gradient')
                optimizer.step();updates+=1
                if updates<=3:step_log.append({'updates':updates,'dose':epoch,'exposures':exposures,'global_gradient_norm_before_clip':float(norm),'loss_terms':last_details})
            if epoch in DOSES:
                measured=measurement(model,subset,bank,bundles,graphs,c,library,folder/'temporary')
                record={'dose':epoch,'updates':updates,'exposures':exposures,'elapsed_seconds':time.monotonic()-trial_start,
                        'groups':measured['groups'],'last_loss_terms':last_details}
                history.append(record);write(folder/'history.json',history)
                print(json.dumps({'variant':variant['name'],**{k:v for k,v in record.items() if k!='last_loss_terms'}}),flush=True)
                if time.monotonic()-trial_start>a.trial_minutes*60:stop='resource-cap;not-fit';break
                if time.monotonic()-started>a.suite_minutes*60:stop='suite-resource-cap;not-fit';break
        save_file({k:v.detach().cpu().contiguous() for k,v in model.state_dict().items()},str(folder/'model.safetensors'))
        final=measurement(model,subset,bank,bundles,graphs,c,library,folder/'fixed-final',save=True)
        inferred=measurement(model,subset,bank,bundles,graphs,c,library,folder/'inferred-final',inferred=True,save=True)
        receipt={'status':'completed-diagnostic','variant':variant,'history':history,'first_update_diagnostics':step_log,
                 'stopping_reason':stop,'updates':updates,'exposures':exposures,'initializer_sha256':prep['expanded_initializer_sha256'],
                 'model_sha256':digest(folder/'model.safetensors'),'fixed_final':final,'inferred_final':inferred,
                 'elapsed_seconds':time.monotonic()-trial_start,'full_training_executed':False,'Space_deployed':False}
        write(folder/'receipt.json',receipt);completed.append(receipt)
        print(json.dumps({'completed':variant['name'],'fixed':final['groups'],'inferred':inferred['groups'],'seconds':receipt['elapsed_seconds']}),flush=True)
        write(a.output/'progress.json',{'completed':[r['variant']['name'] for r in completed],'elapsed_seconds':time.monotonic()-started})
    write(a.output/'receipt.json',{'status':'completed' if len(completed)==len(comparisons) else 'partial-resource-cap',
          'variants_planned':len(comparisons),'variants_completed':len(completed),'conditions':completed,
          'elapsed_seconds':time.monotonic()-started,'training_cases':10,'twenty_used':False,
          'full_training_executed':False,'Space_deployed':False})
if __name__=='__main__':main()
