"""One-update optimizer/expansion controls on the unchanged original five TRAIN cases."""
import argparse,copy,hashlib,json,sys,time
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import load_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.graph_decoder import SharedGraphDecoder,decode,loss
from img2dwg.structured import encode
from img2dwg.graph_constraints import project
from train_retention_ablation import measurement,make_model,write

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--tiny',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--device',default='cpu');a=p.parse_args()
    torch.set_num_threads(6);torch.manual_seed(20261014);torch.backends.cuda.matmul.allow_tf32=False
    rows=json.loads((a.data/'index.json').read_text())[:5]
    assert all(r['cohort']=='original' and r['split']=='train' for r in rows)
    bank={r['sample_id']:torch.load(a.data/r['sample_id']/'features.pt',weights_only=True).to(a.device) for r in rows}
    bundles={r['sample_id']:json.loads((a.data/r['sample_id']/'components.json').read_text(encoding='utf-8')) for r in rows}
    graphs={r['sample_id']:json.loads((a.data/r['sample_id']/'target.json').read_text(encoding='utf-8')) for r in rows}
    results=[]
    for shape,optimizer_name,lr in [('tiny','Adam',1e-4),('expanded','Adam',1e-4),
                                    ('expanded','Adam',3e-5),('expanded','Adam',1e-6),('expanded','SGD',1e-4)]:
        start=time.monotonic();folder=a.output/(shape+'-'+optimizer_name+'-'+str(lr))
        root=a.tiny if shape=='tiny' else a.data
        c=json.loads((root/'config.json').read_text());lib=json.loads((root/'library.json').read_text(encoding='utf-8'))
        c['diagnostic_fixed_capacity']=[959,726]
        if shape=='tiny':
            model=SharedGraphDecoder(c['nodes'],c['components'],len(c['texts']),hidden=c['hidden'],templates=c['templates'],
              coord_digits=c['coord_digits'],measure_digits=c['measure_digits'],minimum_nodes=959,minimum_components=726).to(a.device)
            weight_path=a.tiny/'model.safetensors'
        else:model=make_model(c,a.device);weight_path=a.data/'initializer.safetensors'
        model.load_state_dict(load_file(str(weight_path)))
        vocab={t:i for i,t in enumerate(c['texts'])};tv={key:i+1 for i,key in enumerate(sorted(lib))}
        targets=[{k:torch.from_numpy(v).to(a.device) for k,v in encode(bundles[r['sample_id']],vocab,tv,c['coord_digits'],c['measure_digits']).items()} for r in rows]
        before=measurement(model,rows,bank,bundles,graphs,c,lib,folder/'before',save=True)
        with torch.no_grad():
            prior={r['sample_id']:project(decode(model(bank[r['sample_id']],capacities=[959,726]),c['texts'],templates=lib)) for r in rows}
        optimizer=getattr(torch.optim,optimizer_name)(model.parameters(),lr=lr)
        model.train();pred=model(torch.cat(list(bank.values())),capacities=[959,726]);value,terms,_=loss(pred,targets)
        value.backward();gradient_norm=float(torch.nn.utils.clip_grad_norm_(model.parameters(),5.))
        weights={name:par.detach().clone() for name,par in model.named_parameters()}
        optimizer.step()
        delta_norm=float(torch.sqrt(sum((par.detach()-weights[name]).square().sum() for name,par in model.named_parameters())))
        del pred,weights,value
        after=measurement(model,rows,bank,bundles,graphs,c,lib,folder/'after',save=True)
        deltas=[]
        with torch.no_grad():
            for r in rows:
                key=r['sample_id'];out=project(decode(model(bank[key],capacities=[959,726]),c['texts'],templates=lib))
                aa=prior[key];used=sorted({n for comp in aa['components'] for n in comp['nodes']})
                movement=np.asarray(out['nodes_mm'])[used]-np.asarray(aa['nodes_mm'])[used]
                translation=np.median(movement,axis=0)
                old={comp['id']:comp for comp in aa['components']};new={comp['id']:comp for comp in out['components']}
                common=[key for key in old if key in new and old[key]['kind']==new[key]['kind']]
                metric=next(m for m in after['rows'] if m['sample_id']==key)
                details=metric['dimension_details']
                deltas.append({'sample_id':key,'median_translation_mm':translation.tolist(),
                   'movement_after_median_translation_p90_mm':float(np.percentile(np.linalg.norm(movement-translation,axis=-1),90)),
                   'same_type_queries':len(common),'queries_with_changed_references':sum(old[k]['nodes']!=new[k]['nodes'] for k in common),
                   'numeric_within_1mm_ignoring_position':sum(d['numeric_error_mm']<=1 for d in details),
                   'physical_length_within_1mm_ignoring_position':sum(d['geometry_error_mm']<=1 for d in details)})
        receipt={'shape':shape,'optimizer':optimizer_name,'lr':lr,'updates':1,'image_exposures':5,'device':a.device,
                 'initializer_sha256':hashlib.sha256(weight_path.read_bytes()).hexdigest(),
                 'gradient_norm_before_clip':gradient_norm,'parameter_update_L2':delta_norm,'initial_loss_terms':terms,
                 'before':before['groups'],'after':after['groups'],'internal_query_movement':deltas,
                 'elapsed_seconds':time.monotonic()-start,'Space_deployed':False,'full_training_executed':False}
        write(folder/'receipt.json',receipt);results.append(receipt);print(json.dumps(receipt),flush=True)
    write(a.output/'receipt.json',{'status':'completed-one-update-controls','conditions':results,'new_training_cases':0,
              'twenty_used':False,'full_training_executed':False,'Space_deployed':False})
if __name__=='__main__':main()
