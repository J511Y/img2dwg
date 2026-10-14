"""Independent TRAIN10 readback: image-only forward, then supervised inspection.

Fresh mode recomputes DINO features from the actual images. The forward pass
receives neither target graphs nor sample identities. No holdout is accepted.
"""
import argparse,json,sys,time
from pathlib import Path
import torch
from safetensors.torch import load_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.graph_adapter import ProtectedGraphAdapter
from scripts.train_retention_ablation import digest,make_model,measurement,write

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--fresh-features',action='store_true');p.add_argument('--reference-radius-mm',type=float)
    p.add_argument('--set-selection',choices=['no-object','image-count-topk'],default='no-object');p.add_argument('--dimension-consistency-mm',type=float)
    p.add_argument('--projection-limit-mm',type=float);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use a fresh verification directory')
    started=time.monotonic();torch.set_num_threads(6)
    rows=json.loads((a.data/'index.json').read_text());c=json.loads(a.config.read_text())
    assert len(rows)==10 and all(r['split']=='train' for r in rows)
    ad=c['adapter'];model=ProtectedGraphAdapter(make_model(c,'cpu'),None,nodes=ad['nodes'],components=ad['components'],
        hidden=ad['hidden'],base_capacity=ad['base_capacity'],protected_rank=ad['protected_rank'],query_nonlinear=ad.get('query_nonlinear',False)).eval()
    model.load_state_dict(load_file(str(a.checkpoint)));bank={};bundles={};graphs={};diffs={}
    if a.fresh_features:
        from transformers import AutoModel
        from img2dwg.model import BACKBONE,REVISION
        from scripts.train_raw_pairs import features
        encoder=AutoModel.from_pretrained(BACKBONE,revision=REVISION).eval();encoder.requires_grad_(False)
    for r in rows:
        k=r['sample_id'];d=a.data/k
        for name,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256'),('features.pt','features_sha256')]:
            assert digest(d/name)==r[field]
        cached=torch.load(d/'features.pt',weights_only=True)
        bank[k]=features(encoder,d/'input.png','cpu') if a.fresh_features else cached
        diffs[k]=float((bank[k]-cached).abs().max())
        bundles[k]=json.loads((d/'components.json').read_text(encoding='utf-8'));graphs[k]=json.loads((d/'target.json').read_text(encoding='utf-8'))
    library=json.loads((a.data/'library.json').read_text(encoding='utf-8'))
    result=measurement(model,rows,bank,bundles,graphs,c,library,a.output/'inferred-final',inferred=True,save=True,reference_radius_mm=a.reference_radius_mm,set_selection=a.set_selection,dimension_consistency_mm=a.dimension_consistency_mm,projection_limit_mm=a.projection_limit_mm)
    write(a.output/'receipt.json',{'schema':'protected-adapter-independent-evaluation/v1','model_sha256':digest(a.checkpoint),
        'config_sha256':digest(a.config),'fresh_image_features':a.fresh_features,'feature_max_absolute_differences':diffs,
        'reference_radius_mm':a.reference_radius_mm,
        'set_selection':a.set_selection,
        'dimension_consistency_mm':a.dimension_consistency_mm,
        'projection_limit_mm':a.projection_limit_mm,
        'model_forward_inputs':'vision features only;fixed query reserve;active/no-object selection',
        'target_CAD_used_only_after_forward_for_evaluation':True,'holdout_accessed':False,'Space_deployed':False,
        'evaluation':result,'elapsed_seconds':time.monotonic()-started})
    print(json.dumps(result['groups']))
if __name__=='__main__':main()
