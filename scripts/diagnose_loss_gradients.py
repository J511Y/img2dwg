"""Measure named legacy-loss gradients at the original fitted checkpoint, no updates."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import torch
from safetensors.torch import load_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.graph_decoder import SharedGraphDecoder,loss
from img2dwg.structured import encode

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--tiny',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(6);torch.manual_seed(20261014)
    c=json.loads((a.tiny/'config.json').read_text());lib=json.loads((a.tiny/'library.json').read_text(encoding='utf-8'))
    rows=json.loads((a.data/'index.json').read_text())[:5];assert all(r['cohort']=='original' for r in rows)
    m=SharedGraphDecoder(c['nodes'],c['components'],len(c['texts']),hidden=c['hidden'],templates=c['templates'],
         coord_digits=c['coord_digits'],measure_digits=c['measure_digits'])
    m.load_state_dict(load_file(str(a.tiny/'model.safetensors')))
    vocab={t:i for i,t in enumerate(c['texts'])};tv={key:i+1 for i,key in enumerate(sorted(lib))}
    features=torch.cat([torch.load(a.data/r['sample_id']/'features.pt',weights_only=True) for r in rows])
    targets=[{k:torch.from_numpy(v) for k,v in encode(json.loads((a.data/r['sample_id']/'components.json').read_text(encoding='utf-8')),vocab,tv,c['coord_digits'],c['measure_digits']).items()} for r in rows]
    started=time.monotonic();pred=m(features);total,details,matches=loss(pred,targets);params=tuple(m.parameters())
    full=torch.autograd.grad(total,params,retain_graph=True,allow_unused=True)
    full_norm=torch.sqrt(sum(g.square().sum() for g in full if g is not None));result=[]
    weights={'node':100,'node_precision':1,'proposal':40,'node_objectness':1,'type':1,'pointer':1,
             'parameter':20,'role':.2,'numeric':1,'text':.3,'template':1,'bearing':1,'scalar':1,
             'axis':.3,'host':.3,'dimension':4,'count':1}
    for name in ['node','proposal','parameter','pointer','axis','node_precision','dimension','count','template']:
        removed,_,_=loss(pred,targets,matches,term_weights={name:0});term=total-removed
        grads=torch.autograd.grad(term,params,retain_graph=True,allow_unused=True)
        norm=torch.sqrt(sum(g.square().sum() for g in grads if g is not None))
        dot=sum((g*f).sum() for g,f in zip(grads,full) if g is not None and f is not None)
        row={'term':name,'weight':weights[name],'unweighted_loss':details[name],
             'weighted_gradient_L2':float(norm),'cosine_with_total_gradient':float(dot/(norm*full_norm).clamp_min(1e-20))}
        result.append(row);print(json.dumps(row),flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({'status':'completed','training_updates':0,'cases':5,'device':'CPU',
        'source_model_sha256':hashlib.sha256((a.tiny/'model.safetensors').read_bytes()).hexdigest(),
        'total_gradient_L2':float(full_norm),'total_loss':float(total.detach()),'terms':result,
        'elapsed_seconds':time.monotonic()-started,'Space_deployed':False,'twenty_used':False},indent=2)+'\n')
if __name__=='__main__':main()
