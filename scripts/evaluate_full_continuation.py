"""Fresh CPU image inference after the full-training candidate is frozen.

No training/threshold mutation occurs here. The twenty is evaluated once;
labels are used by evaluation only and are never given to model.forward.
"""
import argparse,json,shutil,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from transformers import AutoModel
from safetensors.torch import load_file
from img2dwg.graph_loading import build_graph_model
from img2dwg.model import BACKBONE,REVISION
from scripts.train_full_continuation import summarize,DECODER
from scripts.train_retention_ablation import measurement,digest,write
from scripts.train_raw_pairs import features

def main():
    p=argparse.ArgumentParser();p.add_argument('--training-data',type=Path,required=True);p.add_argument('--twenty-data',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Preserve the first frozen-candidate evaluation')
    torch.set_num_threads(6);started=time.monotonic();cp=a.checkpoint
    c=json.loads((cp.parent/'config.json').read_text());assert c['decoder']==DECODER
    freeze=json.loads((cp.parent/'candidate-freeze.json').read_text());assert digest(cp)==freeze['model_sha256']
    training=json.loads((a.training_data/'index.json').read_text());ten=[r for r in training if r['cohort'] in ('original','additional')]
    twenty=json.loads((a.twenty_data/'index.json').read_text());assert len(ten)==10 and len(twenty)==20 and all(r['split']=='validation' for r in twenty)
    assert not {r['group_id'] for r in training if r['split']=='train'}&{r['group_id'] for r in twenty}
    assert not {r['input_sha256'] for r in training if r['split']=='train'}&{r['input_sha256'] for r in twenty}
    model=build_graph_model(c).eval();model.load_state_dict(load_file(str(cp)))
    encoder=AutoModel.from_pretrained(BACKBONE,revision=REVISION).eval();encoder.requires_grad_(False)
    library=json.loads((cp.parent/'library.json').read_text(encoding='utf-8'));results={};diffs={}
    for name,rows,data in [('retention',ten,a.training_data),('twenty',twenty,a.twenty_data)]:
        bank={};bundles={};graphs={}
        for i,r in enumerate(rows):
            k=r['sample_id'];d=data/k
            for file,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256')]:assert digest(d/file)==r[field]
            bank[k]=features(encoder,d/'input.png','cpu')
            if name=='retention':diffs[k]=float((bank[k]-torch.load(d/'features.pt',weights_only=True)).abs().max())
            bundles[k]=json.loads((d/'components.json').read_text(encoding='utf-8'));graphs[k]=json.loads((d/'target.json').read_text(encoding='utf-8'))
            # Source/GT artifacts are separate from predictions in the review.
            dest=a.output/'review-data'/k;dest.mkdir(parents=True)
            for file in ['input.png','target.json','components.json']:shutil.copy2(d/file,dest/file)
        evaluated=measurement(model,rows,bank,bundles,graphs,c,library,a.output/(name+'-final'),inferred=True,save=True,compact_artifacts=True,**DECODER)
        results[name]={'aggregate':summarize(evaluated),'rows':evaluated['rows']}
        print(json.dumps({'fresh_CPU_group':name,**results[name]['aggregate']}),flush=True)
        if name=='twenty':
            # Pre-registered EXP-053 baseline, also frozen before this evaluation.
            # This comparison never feeds candidate selection or tuning.
            bc=json.loads((a.training_data/'source/config.json').read_text());baseline=build_graph_model(bc).eval()
            bp=a.training_data/'source/model.safetensors';baseline.load_state_dict(load_file(str(bp)))
            bm=measurement(baseline,rows,bank,bundles,graphs,bc,library,a.output/'baseline-twenty',inferred=True,save=True,compact_artifacts=True,**DECODER)
            results['baseline_twenty']={'aggregate':summarize(bm),'rows':bm['rows'],'model_sha256':digest(bp)}
            print(json.dumps({'frozen_EXP053_baseline':results['baseline_twenty']['aggregate']}),flush=True)
    assert digest(cp)==freeze['model_sha256']
    write(a.output/'index.json',ten+twenty)
    passed=results['retention']['aggregate']['passed_cases']==10 and results['twenty']['aggregate']['passed_cases']==20
    write(a.output/'receipt.json',{'schema':'full-continuation-fresh-evaluation/v1','status':'numeric-passed' if passed else 'quality-failed',
        'model_sha256':digest(cp),'candidate_frozen_before_twenty':True,'config_sha256':digest(cp.parent/'config.json'),
        'twenty_cohort':'existing19 + one pretraining metadata-only pixel-leak replacement',
        'fresh_image_features':True,'feature_device':'CPU','model_device':'CPU','retention_feature_max_abs_differences':diffs,
        'retention':results['retention'],'twenty':results['twenty'],'twenty_used_for_selection':False,
        'baseline_twenty':results['baseline_twenty'],
        'forward_inputs':'vision features only; no target CAD, no identity, no target count','decoder':DECODER,
        'elapsed_seconds':time.monotonic()-started,'visual_inspection_pending':True,'Space_release_allowed':False})
if __name__=='__main__':main()
