"""Bounded 1,028-pair residual training with immutable ten-case retention.

No held-out twenty is present in this runner's input archive. Selection uses
the previously fixed development sixteen; actual native CAD metrics, rather
than training loss or an arbitrary step count, control quality stopping.
"""
import argparse,copy,json,math,os,random,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from safetensors.torch import load_file,save_file
from img2dwg.graph_adapter import ProtectedGraphAdapter
from img2dwg.graph_loading import build_graph_model
from img2dwg.graph_decoder import loss
from img2dwg.graph_update import coordinate_snapshot,guarded_step
from img2dwg.graph_evaluation import PROTOCOL,QualityStopper
from img2dwg.structured import encode
from img2dwg.raw_evaluation import aggregate
from scripts.train_retention_ablation import digest,measurement,write

DECODER=dict(set_selection='image-count-topk',dimension_consistency_mm=10.,projection_limit_mm=10.)

def summarize(result):
    rr=result['rows'];g=aggregate(rr)
    for k in ['component_f1','shared_reference_f1']:g[k]=float(np.mean([r[k] for r in rr])) if rr else 0.
    g['geometry_candidate_cases']=sum(r['geometry_candidate_without_DXF_audit'] for r in rr)
    distances=[r['referenced_node_set_chamfer_mm'] for r in rr if r.get('referenced_node_set_chamfer_mm') is not None]
    g['referenced_node_set_chamfer_mm']=float(np.mean(distances)) if len(distances)==len(rr) and rr else None
    return g

def selection_score(g):
    fraction=g['dimensions_correct_geometry_and_value']/max(g['required_dimensions'],1)
    distance=g.get('referenced_node_set_chamfer_mm')
    physical=.1/(1+distance/1000) if distance is not None else 0.
    return g['structure_f1']+g['component_f1']+g['shared_reference_f1']+fraction+physical

def make_continuation(c,bank,retention,rows,device):
    base=build_graph_model(c).to(device)
    train=[r for r in rows if r['split']=='train']
    capacity=[math.ceil(max(r['nodes'] for r in train)*1.25)+32,math.ceil(max(r['component_count'] for r in train)*1.25)+32]
    inner=c['adapter'];base_capacity=[inner['nodes'],inner['components']]
    model=ProtectedGraphAdapter(base,[bank[r['sample_id']] for r in retention],nodes=capacity[0],components=capacity[1],
        hidden=128,base_capacity=base_capacity,padding_policy='preserve-prefix').to(device)
    config={**c,'adapter_stack':[copy.deepcopy(inner),{'type':'protected-feature-residual/v1','hidden':128,
        'nodes':capacity[0],'components':capacity[1],'base_capacity':base_capacity,'protected_rank':model.protected_rank,
        'zero_tolerance':model.zero_tolerance,'padding_policy':'preserve-prefix','source_CAD_or_case_id_access':False}],
        'decoder':DECODER,'full_training_cases':1028,'retention_cases':10,
        'capacity_policy':'1.25 * training maximum + 32;fixed set, never GT prefix',
        'training_count_teacher_forcing':False,'inference_count_from_image':True}
    config.pop('adapter',None)
    return model,config

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--device',default='cuda');p.add_argument('--minutes',type=float,default=180)
    p.add_argument('--preflight-only',action='store_true');p.add_argument('--lr',type=float,default=.0003)
    a=p.parse_args();torch.set_num_threads(6);torch.manual_seed(20261015);random.seed(20261015);np.random.seed(20261015)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    if a.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA job required')
    if (a.output/'manifest.json').exists():raise FileExistsError('Published experiment is immutable')
    rows=json.loads((a.data/'index.json').read_text());prep=json.loads((a.data/'preparation.json').read_text())
    training=[r for r in rows if r['split']=='train'];dev=[r for r in rows if r['cohort']=='development']
    retention=[r for r in rows if r['cohort'] in ('original','additional')]
    if len(training)!=1028 or len(dev)!=16 or len(retention)!=10 or len(rows)!=1044:raise ValueError('Full train/development contract changed')
    if len({r['sample_id'] for r in training})!=1028:raise ValueError('Training case IDs must be unique')
    if prep['twenty_accessed'] or any(r['cohort']=='twenty' for r in rows):raise ValueError('Twenty must remain outside training archive')
    if {r['group_id'] for r in training}&{r['group_id'] for r in dev}:raise ValueError('Group overlap')
    c=json.loads((a.data/'source/config.json').read_text());library=json.loads((a.data/'library.json').read_text(encoding='utf-8'))
    bank={};bundles={};graphs={};targets={};vocab={v:i for i,v in enumerate(c['texts'])};tv={k:i+1 for i,k in enumerate(sorted(library))}
    source=a.data/'source/model.safetensors';assert digest(source)==prep['source_model_sha256']
    for r in rows:
        key=r['sample_id'];d=a.data/key
        for name,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256'),('features.pt','features_sha256')]:
            if digest(d/name)!=r[field]:raise ValueError('Immutable artifact changed: '+key+'/'+name)
        bank[key]=torch.load(d/'features.pt',weights_only=True).to(a.device)
        bundles[key]=json.loads((d/'components.json').read_text(encoding='utf-8'));graphs[key]=json.loads((d/'target.json').read_text(encoding='utf-8'))
        if r['split']=='train':targets[key]={k:torch.from_numpy(v).to(a.device) for k,v in encode(bundles[key],vocab,tv,c['coord_digits'],c['measure_digits']).items()}
    model,config=make_continuation(c,bank,retention,rows,a.device);model.base.load_state_dict(load_file(str(source)))
    write(a.output/'config.json',config);write(a.output/'library.json',library)
    norms={r['sample_id']:float(model.protected_features(bank[r['sample_id']]).norm()) for r in retention}
    assert not any(norms.values()),norms
    write(a.output/'manifest.json',{'schema':'img2dwg-full-continuation/v1','source_model_sha256':digest(source),
        'train_ids':[r['sample_id'] for r in training],'development_ids':[r['sample_id'] for r in dev],
        'retention_ids':[r['sample_id'] for r in retention],'twenty_used_for_selection':False,
        'seed':20261015,'decoder':DECODER,'quality_protocol':PROTOCOL,'wall_clock_training_cap_minutes':a.minutes,
        'source_code_sha256':os.getenv('CODE_SHA256'),'data_archive_sha256':os.getenv('TRAINING_ARCHIVE_SHA256'),
        'optimizer':'fresh Adam only on zero-output new branch; entire verified model frozen, source Adam not restarted',
        'learning_rate':a.lr,'protected_feature_rank':model.protected_rank,'retention_projection_norms':norms,
        'loss_weights':'unchanged DEFAULT_LOSS_WEIGHTS','coordinate_update_limit_mm':50.,'gradient_clip':5.,
        'batch':'one observation; all queries, no target capacity crop','assignment_refresh':'each example after 20 full passes',
        'backbone_feature_device':'CPU;same implementation as fresh serving','training_loss_is_pass_criterion':False,
        'minimum_coverage_before_selection':'every one of 1028 training observations exposed',
        'plateau_eligibility':'three full dataset passes; five stale native quality checks per LR level, three levels',
        'Space_release_allowed':False,'source_CAD_retrieval_in_forward':False})
    def measure(rr,name,save=True):
        m=measurement(model,rr,bank,bundles,graphs,config,library,a.output/name,inferred=True,save=save,compact_artifacts=True,**DECODER)
        return {'aggregate':summarize(m),'rows':m['rows']}
    initial=measure(retention,'initial-retention')
    write(a.output/'initial-retention.json',initial)
    if initial['aggregate']['passed_cases']!=10 or initial['aggregate']['dimensions_correct_geometry_and_value']!=252:
        raise ValueError('Expanded initializer failed actual 10-case native retention')
    params=[x for x in model.parameters() if x.requires_grad]
    if not params or any(x.requires_grad for x in model.base.parameters()):raise ValueError('Verified complete model must be frozen')
    def save(name):save_file({k:v.detach().cpu().contiguous() for k,v in model.state_dict().items()},str(a.output/name))
    save('initializer.safetensors')
    if a.preflight_only:
        write(a.output/'preflight.json',{'status':'passed','native_cases':10,'native_dimensions':252,'capacity':model.fixed_capacity,'training_executed':False});return
    optimizer=torch.optim.Adam(params,lr=a.lr);stopper=QualityStopper();matches={};history=[];guards=[]
    probe=sorted([r for r in training if r not in retention],key=lambda r:__import__('hashlib').sha256(('train-probe-20261015'+r['sample_id']).encode()).hexdigest())[:16]
    started=time.monotonic();last_check=started;epoch=0;updates=0;accepted=0;seen=set();best=-float('inf');status='resource-cap-reached-not-quality-pass'
    def check(force=False):
        nonlocal last_check,best,status
        if not force and time.monotonic()-last_check<300:return False
        ret=measure(retention,'retention-preview');de=measure(dev,'development-preview');pr=measure(probe,'training-probe')
        old_ok=ret['aggregate']['passed_cases']==10 and ret['aggregate']['dimensions_correct_geometry_and_value']==252
        score=selection_score(de['aggregate']);eligible=len(seen)==1028
        all_ok=old_ok and de['aggregate']['passed_cases']==16 and pr['aggregate']['passed_cases']==16
        action='continue';improved=False
        if eligible and epoch>=3:action,improved=stopper.update(score,all_ok)
        elif eligible and all_ok:action,improved=stopper.update(score,True)
        if eligible and old_ok and score>best:
            best=score;save('best.safetensors')
            torch.save({'optimizer':optimizer.state_dict(),'matches':{k:tuple(t.cpu() for t in v) for k,v in matches.items()},
                'epoch':epoch,'updates':updates,'seen':sorted(seen)},a.output/'best-optimizer-and-assignment.pt')
            write(a.output/'best-evaluation.json',{'development':de,'retention':ret,'training_probe':pr,'updates':updates,'epoch':epoch,'score':score,
                'model_sha256':digest(a.output/'best.safetensors')})
        quality_checkpoint=None
        if eligible and all_ok:
            quality_checkpoint=f'quality-{updates}.safetensors';save(quality_checkpoint)
            write(a.output/f'quality-{updates}.json',{'checkpoint':quality_checkpoint,'model_sha256':digest(a.output/quality_checkpoint),
                'development':de,'retention':ret,'training_probe':pr,'native_DXF_checks_executed':True,'updates':updates})
        record={'epoch':epoch,'updates':updates,'accepted_updates':accepted,'unique_training_exposed':len(seen),
            'elapsed_seconds':time.monotonic()-started,'score':score,'action':action,'selection_eligible':eligible,
            'retention':ret['aggregate'],'development':de['aggregate'],'training_probe':pr['aggregate'],
            'lr':optimizer.param_groups[0]['lr'],'max_memory_allocated_bytes':torch.cuda.max_memory_allocated() if a.device=='cuda' else None}
        record['quality_checkpoint']=quality_checkpoint
        history.append(record);write(a.output/'quality-history.json',history);write(a.output/'progress.json',record)
        write(a.output/'guard-history.json',guards);print(json.dumps(record),flush=True)
        last_check=time.monotonic()
        if not old_ok:status='failed-retention';return True
        if action=='reduce-learning-rate':
            for group in optimizer.param_groups:group['lr']*=.3
        if action in ('quality-passed','quality-plateau'):status=action;return True
        return False
    while time.monotonic()-started<a.minutes*60:
        epoch+=1;order=training.copy();random.Random(20261015+epoch).shuffle(order)
        for r in order:
            key=r['sample_id'];model.train();optimizer.zero_grad(set_to_none=True)
            pred=model(bank[key]);known=[matches[key]] if key in matches and epoch%20 else None
            value,details,matched=loss(pred,[targets[key]],known)
            if not torch.isfinite(value):raise ValueError('Nonfinite graph loss')
            value.backward();norm=torch.nn.utils.clip_grad_norm_(params,5.)
            if not torch.isfinite(norm):raise ValueError('Nonfinite gradient')
            del pred
            def capture():
                with torch.no_grad():return {key:coordinate_snapshot(model(bank[key]))}
            guard=guarded_step(model,optimizer,capture,{},[],step_mm=50.,retention_mm=10.)
            updates+=1;accepted+=int(guard['accepted']);seen.add(key);matches[key]=matched[0]
            guards.append({'update':updates,'sample_id':key,**guard})
            if updates%25==0:
                write(a.output/'training-progress.json',{'epoch':epoch,'updates':updates,'accepted_updates':accepted,'unique_training_exposed':len(seen),'elapsed_seconds':time.monotonic()-started,'loss':float(value.detach()),'last_terms':details})
                print(json.dumps({'epoch':epoch,'updates':updates,'seen':len(seen),'accepted':accepted,'loss':float(value.detach()),'seconds':time.monotonic()-started}),flush=True)
            if check() or time.monotonic()-started>=a.minutes*60:break
        if status in ('failed-retention','quality-passed','quality-plateau'):break
    check(force=True);save('last.safetensors')
    torch.save({'optimizer':optimizer.state_dict(),'matches':{k:tuple(t.cpu() for t in v) for k,v in matches.items()},'epoch':epoch,'updates':updates,'seen':sorted(seen)},a.output/'last-optimizer-and-assignment.pt')
    selected=a.output/'best.safetensors'
    if selected.exists():model.load_state_dict(load_file(str(selected)))
    else:selected=a.output/'last.safetensors'
    save_file({k:v.detach().cpu().contiguous() for k,v in model.base.state_dict().items()},str(a.output/'frozen-base.safetensors'))
    frozen_base_sha=digest(a.output/'frozen-base.safetensors')
    if frozen_base_sha!=digest(source):raise ValueError('Frozen verified model changed')
    final_ret=measure(retention,'retention-final');final_dev=measure(dev,'development-final');final_probe=measure(probe,'training-probe-final')
    save('model.safetensors')
    receipt={'schema':'img2dwg-full-continuation-result/v1','execution_status':'completed','quality_status':'passed-development' if status=='quality-passed' else 'not-passed',
        'stopping_reason':status,'epochs_started':epoch,'updates':updates,'accepted_updates':accepted,'unique_training_exposed':len(seen),
        'full_training_dataset_cases':1028,'complete_first_pass':len(seen)==1028,'elapsed_seconds':time.monotonic()-started,
        'model_sha256':digest(a.output/'model.safetensors'),'selected_checkpoint':selected.name,'retention':final_ret,
        'frozen_base_sha256':frozen_base_sha,
        'development':final_dev,'training_probe':final_probe,'twenty_accessed':False,'Space_release_allowed':False,
        'visual_inspection_pending':True,'source_CAD_retrieval_in_forward':False}
    write(a.output/'receipt.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k not in ('retention','development','training_probe')}),flush=True)
if __name__=='__main__':main()
