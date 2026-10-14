"""Quality-stopped five-pair/full-data graph learning on real source images."""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import save_file,load_file
from transformers import AutoModel
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.model import BACKBONE,REVISION
from img2dwg.structured import encode,compile_graph
from img2dwg.graph_decoder import SharedGraphDecoder,loss,decode
from img2dwg.graph_constraints import project
from img2dwg.graph_evaluation import evaluate,PROTOCOL,QualityStopper
from img2dwg.raw_evaluation import aggregate
from img2dwg.vector import exports,svg
from train_raw_pairs import features


def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


@torch.no_grad()
def evaluate_rows(model,records,data,output,bank,texts,targets,epoch,save=True,library=None):
    model.eval(); results=[]; node_errors=[]
    for r in records:
        key=r['sample_id']; raw=decode(model(bank[key]),texts,templates=library); solved=project(raw)
        compile_error=None
        try:graph=compile_graph(solved,strict=False)
        except ValueError as exc:
            compile_error=str(exc);graph={**solved['frame'],'components':[],'texts':[],'compiler_failed':compile_error}
        target=json.loads((data/key/'target.json').read_text(encoding='utf-8'))
        gt=json.loads((data/key/'components.json').read_text(encoding='utf-8'))
        error=compile_error; factory=None; folder=output/key
        try:
            if save:factory=exports(graph,folder)
            else:
                # Fast metric checkpoints still audit actual DXF. Temporary
                # files are replaced only within this new experimental run.
                factory=exports(graph,folder)
        except Exception as exc:error=type(exc).__name__+': '+str(exc)
        metric=evaluate(solved,gt,graph,target,factory); metric.update(sample_id=key,split=r['split'],epoch=epoch,export_error=error)
        try:raw_graph=compile_graph(raw,strict=False)
        except ValueError:raw_graph={**raw['frame'],'components':[],'texts':[]}
        raw_metric=evaluate(raw,gt,raw_graph,target,factory)
        metric['before_constraints']={k:raw_metric[k] for k in ('structure_f1','component_f1','shared_reference_f1')}
        results.append(metric)
        # Unordered node set distances are diagnostics, not a substitute for
        # the structure/dimension checks or a post-hoc fit to the CAD.
        xy=np.asarray(solved['nodes_mm']); truth=np.asarray(gt['nodes_mm'])
        selected=sorted({n for c in solved['components'] for n in c['nodes']})
        if selected:
            distance=np.linalg.norm(xy[selected,None]-truth[None],axis=-1)
            node_errors.append(float(np.median(distance.min(0))))
        else:node_errors.append(10000.)
        folder.mkdir(parents=True,exist_ok=True); write(folder/'metrics.json',metric); write(folder/'shared-graph.json',solved)
        (folder/'raw.svg').write_text(svg(raw_graph),encoding='utf-8')
    agg=aggregate(results)
    for key in ('component_f1','shared_reference_f1','host_recall'):
        agg[key]=float(np.mean([r[key] for r in results])) if results else 0.
    agg['median_node_set_error_mm']=float(np.median(node_errors)) if node_errors else None
    return {'aggregate':agg,'rows':results}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--data',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stage',choices=['tiny','full','evaluate'],required=True); parser.add_argument('--minutes',type=float,default=30)
    parser.add_argument('--resume',type=Path);parser.add_argument('--initialize',type=Path); parser.add_argument('--lr',type=float,default=.0001); args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True); device='cuda'
    if not torch.cuda.is_available():raise RuntimeError('Bounded cloud GPU required')
    torch.set_num_threads(6);torch.backends.cuda.matmul.allow_tf32=False
    random.seed(20261014);np.random.seed(20261014);torch.manual_seed(20261014)
    records=json.loads((args.data/'index.json').read_text()); summary=json.loads((args.data/'summary.json').read_text(encoding='utf-8'))
    training=[r for r in records if r['cohort']=='five'] if args.stage=='tiny' else [r for r in records if r['split']=='train']
    development=training if args.stage=='tiny' else [r for r in records if r['cohort']=='development']
    twenty=[r for r in records if r['cohort']=='twenty']
    assert len([r for r in records if r['cohort']=='five'])==5 and len(twenty)==20
    assert not {r['group_id'] for r in training}&{r['group_id'] for r in twenty}
    texts=summary['text_vocabulary'];vocab={text:i for i,text in enumerate(texts)}
    library=json.loads((args.data/'library.json').read_text(encoding='utf-8')) if (args.data/'library.json').exists() else {}
    template_vocab={key:i+1 for i,key in enumerate(sorted(library))}
    nodes=max(r['nodes'] for r in training)+32;components=max(r['component_count'] for r in training)+32
    coord_digits=8 if args.stage!='tiny' else 6;measure_digits=6 if args.stage!='tiny' else 5;adaptive=args.stage!='tiny'
    initializer_config=json.loads((args.initialize.parent/'config.json').read_text(encoding='utf-8')) if args.initialize else {}
    minimum_nodes=min(nodes,initializer_config.get('nodes',32));minimum_components=min(components,initializer_config.get('components',32))
    config={'schema':'img2dwg-shared-decoder/v1','nodes':nodes,'components':components,'texts':texts,'hidden':192,
            'backbone':BACKBONE,'backbone_revision':REVISION,'size':512,'protocol':PROTOCOL,'threshold':.5,
            'inference_target_CAD_access':False,'input_domain':'actual-as-built','forward_target_queries':False,
            'templates':len(library)+1,'training_only_local_native_library':True,'coord_digits':coord_digits,
            'measure_digits':measure_digits,'adaptive_capacity':adaptive,
            'minimum_nodes':minimum_nodes,'minimum_components':minimum_components,
            'training_count_teacher_forcing':adaptive,'inference_count_from_image':adaptive}
    if args.resume:
        old=json.loads((args.resume.parent/'config.json').read_text(encoding='utf-8'))
        if old['nodes']!=nodes or old['components']!=components or old['texts']!=texts:
            raise ValueError('Resume architecture differs; use explicit expansion transfer, never silently ignore weights')
    model=SharedGraphDecoder(nodes,components,len(texts),templates=len(library)+1,coord_digits=coord_digits,measure_digits=measure_digits,adaptive_capacity=adaptive,
                             minimum_nodes=minimum_nodes,minimum_components=minimum_components).to(device)
    if args.resume:model.load_state_dict(load_file(str(args.resume)),strict=True)
    initialization=None
    if args.initialize:
        state=load_file(str(args.initialize));current=model.state_dict();copied=[];omitted=[]
        source_config=json.loads((args.initialize.parent/'config.json').read_text(encoding='utf-8'))
        source_library=json.loads((args.initialize.parent/'library.json').read_text(encoding='utf-8'))
        partial=[]
        for key,value in state.items():
            if key in current and current[key].shape==value.shape:current[key]=value;copied.append(key)
            elif key in ('node_queries.weight','component_queries.weight','node_grid','component_grid'):
                count=min(len(value),len(current[key]));current[key][:count]=value[:count];partial.append({'key':key,'prefix':count})
            elif key in ('text.weight','text.bias','template.weight','template.bias'):
                source_labels=source_config['texts'] if key.startswith('text.') else ['<unknown>']+sorted(source_library)
                destination_labels=texts if key.startswith('text.') else ['<unknown>']+sorted(library)
                positions={label:i for i,label in enumerate(destination_labels)};count=0
                for i,label in enumerate(source_labels):
                    if label in positions:current[key][positions[label]]=value[i];count+=1
                partial.append({'key':key,'mapped_labels':count})
            elif key.startswith('node_digits.') or key.startswith('size_digits.'):
                groups=2 if key.startswith('node_digits.') else 7
                old_digits=value.shape[0]//groups//10;new_digits=current[key].shape[0]//groups//10
                if new_digits>=old_digits:
                    dst=current[key].reshape(groups,new_digits,10,*current[key].shape[1:]);src=value.reshape(groups,old_digits,10,*value.shape[1:]);dst[:,-old_digits:]=src
                    if key.endswith('bias'):dst[:,:new_digits-old_digits,0]=8.
                    partial.append({'key':key,'old_digits':old_digits,'new_digits':new_digits})
                else:omitted.append(key)
            else:omitted.append(key)
        model.load_state_dict(current,strict=True)
        initialization={'checkpoint_sha256':digest(args.initialize),'copied':copied,'not_copied':omitted,
                        'new_heads':[k for k in current if k not in copied],'partial_expansion':partial}
    encoder=AutoModel.from_pretrained(BACKBONE,revision=REVISION).to(device).eval();encoder.requires_grad_(False)
    bank={};targets={}; requested=training+development+(twenty if args.stage=='evaluate' else [])
    for r in {r['sample_id']:r for r in requested}.values():
        key=r['sample_id']
        for name,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256')]:
            assert digest(args.data/key/name)==r[field]
        bank[key]=features(encoder,args.data/key/'input.png',device)
        bundle=json.loads((args.data/key/'components.json').read_text(encoding='utf-8'))
        targets[key]={k:torch.from_numpy(v).to(device) for k,v in encode(bundle,vocab,template_vocab,coord_digits,measure_digits).items()}
        if len(bank)%100==0:print(json.dumps({'feature_cache':len(bank)}),flush=True)
    manifest={'stage':args.stage,'train_ids':[r['sample_id'] for r in training],'development_ids':[r['sample_id'] for r in development],
              'twenty_ids':[r['sample_id'] for r in twenty],'seed':20261014,'wall_clock_training_cap_minutes':args.minutes,
              'arbitrary_steps_as_fit':False,'code_sha256':os.getenv('CODE_SHA256'),'data_sha256':os.getenv('TRAINING_ARCHIVE_SHA256'),
              'checkpoint_metric_protocol':PROTOCOL,'source_originals_unchanged':True,'twenty_used_for_selection':False}
    manifest.update(initialization=initialization,tiny_joint_batch=args.stage=='tiny',FP32_TF32_disabled=True,
                    assignment_freeze='after measured median node-set error below 100mm; per-example Hungarian identities retained')
    write(args.output/'config.json',config);write(args.output/'manifest.json',manifest)
    write(args.output/'library.json',library)
    optimizer=torch.optim.Adam(model.parameters(),lr=args.lr);stopper=QualityStopper();started=time.monotonic();last_eval=started
    epoch=0;updates=0;matches={};freeze_matches=False;best=-float('inf');best_path=args.output/'best.safetensors';history=[];status='resource-cap-reached-not-quality-pass'
    def save(path):save_file({k:v.detach().cpu().contiguous() for k,v in model.state_dict().items()},str(path))
    def checkpoint(force=False):
        nonlocal last_eval,best,status,freeze_matches
        if not force and time.monotonic()-last_eval<45:return False
        metric=evaluate_rows(model,development,args.data,args.output/'development-preview',bank,texts,targets,epoch,library=library)
        agg=metric['aggregate']; error=agg['median_node_set_error_mm']
        score=agg['structure_f1']+agg['component_f1']+agg['shared_reference_f1']+agg['dimensions_correct_geometry_and_value']/max(agg['required_dimensions'],1)+1/(1+error/100)
        action,improved=stopper.update(score,agg['passed_cases']==len(development))
        if score>best:best=score;save(best_path);write(args.output/'best-evaluation.json',metric)
        record={'epoch':epoch,'updates':updates,'seconds':time.monotonic()-started,'score':score,'action':action,**agg}
        if args.stage=='tiny' and error<100:freeze_matches=True
        record['assignment_frozen']=freeze_matches
        history.append(record);write(args.output/'quality-history.json',history);write(args.output/'progress.json',record)
        print(json.dumps(record),flush=True);last_eval=time.monotonic()
        if action=='reduce-learning-rate':
            for group in optimizer.param_groups:group['lr']*=.3
        if action in ('quality-passed','quality-plateau'):status=action;return True
        return False
    if args.stage!='evaluate':
        while time.monotonic()-started<args.minutes*60:
            epoch+=1; order=training.copy(); random.shuffle(order)
            batches=[order] if args.stage=='tiny' else [[r] for r in order]
            for batch in batches:
                keys=[r['sample_id'] for r in batch];model.train();optimizer.zero_grad(set_to_none=True)
                capacity=[len(targets[keys[0]]['nodes'])+32,len(targets[keys[0]]['kind'])+32] if adaptive else None
                pred=model(torch.cat([bank[key] for key in keys]),capacities=capacity)
                # Hungarian refresh is based on current predictions. Caching
                # amortizes cubic assignment work; it is not GT index matching.
                cached=[matches[key] for key in keys] if all(key in matches for key in keys) and (freeze_matches or epoch%20) else None
                value,details,matched=loss(pred,[targets[key] for key in keys],cached)
                for key,match in zip(keys,matched):matches[key]=match
                if not torch.isfinite(value):raise ValueError('Non-finite shared graph loss')
                value.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),5.)
                if not torch.isfinite(norm):raise ValueError('Non-finite gradient')
                optimizer.step();updates+=1
                if args.stage=='full' and checkpoint():break
                if updates%100==0:
                    print(json.dumps({'epoch':epoch,'updates':updates,'loss':float(value.detach()),**details}),flush=True)
                if time.monotonic()-started>=args.minutes*60:break
            if status in ('quality-passed','quality-plateau'):break
            if checkpoint():break
        checkpoint(force=True);save(args.output/'last.safetensors')
        model.load_state_dict(load_file(str(best_path)),strict=True)
    train_rows=[r for r in records if r['cohort']=='five']
    for r in train_rows:
        if r['sample_id'] not in bank:bank[r['sample_id']]=features(encoder,args.data/r['sample_id']/'input.png',device)
    five=evaluate_rows(model,train_rows,args.data,args.output/'five-preview',bank,texts,targets,epoch,library=library)
    validation=None
    # The full run/evaluate runs the twenty once after all selection ends.
    if args.stage in ('full','evaluate'):
        for r in twenty:bank[r['sample_id']]=features(encoder,args.data/r['sample_id']/'input.png',device)
        validation=evaluate_rows(model,twenty,args.data,args.output/'twenty-preview',bank,texts,targets,epoch,library=library)
    save(args.output/'model.safetensors')
    receipt={'status':'completed','stopping_reason':status,'epochs':epoch,'updates':updates,'elapsed_seconds':time.monotonic()-started,
             'five':five,'twenty':validation,'model_sha256':digest(args.output/'model.safetensors'),
             'full_training_executed':args.stage=='full','source_CAD_retrieval_in_forward':False,
             'space_release_allowed':False,'visual_inspection_pending':True}
    write(args.output/'receipt.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k not in ('five','twenty')}),flush=True)
if __name__=='__main__':main()
