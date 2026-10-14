"""Five-only inference ablation: learned millimetre bins + continuous residual.

No optimization or twenty-case access. All positions remain model predictions.
"""
import argparse
import copy
import json
import sys
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModel
from safetensors.torch import load_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.model import BACKBONE,REVISION
from img2dwg.graph_decoder import SharedGraphDecoder,decode
from img2dwg.graph_constraints import project
from img2dwg.structured import UNIT,compile_graph
from img2dwg.graph_evaluation import evaluate
from img2dwg.raw_evaluation import aggregate
from img2dwg.vector import exports
from train_raw_pairs import features

def coarse_bin(pred):
    out=dict(pred);p=pred['node_digits'].softmax(-1);d=p.argmax(-1)
    prefix=d[...,:-1];weights=p.new_tensor([10**i for i in range(prefix.shape[-1]-1,-1,-1)])
    base=(prefix*weights).sum(-1);negative=pred['node_sign'].argmax(-1).bool()
    lower=torch.where(negative,-base-.9,base);upper=torch.where(negative,-base,base+.9)
    confident=p[...,:-1,:].amax(-1).amin(-1)>.99
    confident &= pred['node_sign'].softmax(-1).amax(-1)>.99
    xy=pred['xy']*UNIT; out['xy']=torch.where(confident,xy.clamp(min=lower,max=upper),xy)/UNIT
    return out,int(confident.sum())

def unique_refs(bundle,pred):
    out=copy.deepcopy(bundle);before=out['invalid_repeated_references'];changed=0
    for c in out['components']:
        required=len(c['nodes']) if c['kind']=='native_path' else 2 if c['kind'] in ('dimension','centerline','unresolved_edge','symbol') else 1
        used=set();query=int(c['id'][1:])
        for slot in range(required):
            node=c['nodes'][slot]
            if node in used:
                scores=pred['refs'][0,query,slot].detach().cpu().numpy().copy();scores[list(used)]=-np.inf
                node=int(scores.argmax());c['nodes'][slot]=node;changed+=1
            used.add(node)
    out['invalid_repeated_references']=0
    out['schema_reference_decoding']={'original_invalid_components':before,'reference_alternatives':changed,'GT_access':False}
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);torch.set_num_threads(6)
    config=json.loads((args.checkpoint/'config.json').read_text(encoding='utf-8'));library=json.loads((args.checkpoint/'library.json').read_text(encoding='utf-8'))
    m=SharedGraphDecoder(config['nodes'],config['components'],len(config['texts']),templates=config['templates'],hidden=config['hidden'])
    loaded=m.load_state_dict(load_file(str(args.checkpoint/'best.safetensors')),strict=False)
    if loaded.unexpected_keys or any(not name.startswith('count.') for name in loaded.missing_keys):raise ValueError(str(loaded))
    m.eval();encoder=AutoModel.from_pretrained(BACKBONE,revision=REVISION).eval();encoder.requires_grad_(False)
    rows=[r for r in json.loads((args.data/'index.json').read_text()) if r['cohort']=='five'];assert len(rows)==5
    policies=('original-axes-100mm','dimension-only','axes-1mm','axes-1mm-unique-refs')
    all_metrics={name:[] for name in policies}
    cache=args.output.parent/'feature-cache';cache.mkdir(exist_ok=True)
    for r in rows:
        key=r['sample_id'];path=cache/(key+'.pt')
        if path.exists():ft=torch.load(path,weights_only=True)
        else:ft=features(encoder,args.data/key/'input.png','cpu');torch.save(ft,path)
        with torch.no_grad():pred=m(ft)
        modified,count=coarse_bin(pred)
        for name in policies:
            proposal=pred
            b=decode(proposal,config['texts'],templates=library)
            if name.endswith('unique-refs'):b=unique_refs(b,proposal)
            if name=='dimension-only':b['axis_links']=[]
            b=project(b,axis_tolerance_mm=100 if name=='original-axes-100mm' else 1.);g=compile_graph(b,strict=False);out=args.output/name/'five-preview'/key;factory=exports(g,out)
            target=json.loads((args.data/key/'target.json').read_text(encoding='utf-8'));gt=json.loads((args.data/key/'components.json').read_text(encoding='utf-8'))
            metric=evaluate(b,gt,g,target,factory);metric.update(sample_id=key,split='train',confident_millimetre_coordinates=count,policy=name)
            (out/'metrics.json').write_text(json.dumps(metric,indent=2));(out/'shared-graph.json').write_text(json.dumps(b),encoding='utf-8')
            all_metrics[name].append(metric)
            print(json.dumps({'case':key,'policy':name,'passed':metric['passed'],'structure_f1':metric['structure_f1'],'component_f1':metric['component_f1'],
                              'shared_f1':metric['shared_reference_f1'],'dims':metric['components']['dimension']['correct_geometry_and_value'],'coarse_coordinates':count}),flush=True)
    receipt={name:{'aggregate':aggregate(metrics),'rows':metrics} for name,metrics in all_metrics.items()}
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v['aggregate'] for k,v in receipt.items()}))
if __name__=='__main__':main()
