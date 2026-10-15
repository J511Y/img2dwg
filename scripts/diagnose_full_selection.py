"""TRAIN-only post-forward oracle matching; never an inference success claim."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from safetensors.torch import load_file
from img2dwg.graph_loading import build_graph_model
from img2dwg.graph_decoder import assignments
from img2dwg.graph_update import coordinate_snapshot
from img2dwg.structured import encode,MAX_REFS
from scripts.train_retention_ablation import digest,write

@torch.no_grad()
def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--data',type=Path,required=True)
    p.add_argument('--probe-index',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(6);c=json.loads((a.snapshot/'config.json').read_text());model=build_graph_model(c).eval();model.load_state_dict(load_file(str(a.snapshot/'model.safetensors')))
    rows=json.loads(a.probe_index.read_text())[:4];assert len(rows)==4 and all(r['split']=='train' for r in rows)
    lib=json.loads((a.data/'library.json').read_text(encoding='utf-8'));vocab={x:i for i,x in enumerate(c['texts'])};tv={k:i+1 for i,k in enumerate(sorted(lib))};result=[]
    for r in rows:
        k=r['sample_id'];pred=model(torch.load(a.data/k/'features.pt',weights_only=True))
        # CAD labels enter only after the image-only forward call above.
        b=json.loads((a.data/k/'components.json').read_text(encoding='utf-8'));t={k:torch.from_numpy(v) for k,v in encode(b,vocab,tv,c['coord_digits'],c['measure_digits']).items()}
        inverse,ci,cj=assignments(pred,t);node_count,component_count=[max(1,int(round(float(v)))) for v in pred['log_count'][0].exp()]
        active=torch.zeros(pred['xy'].shape[1],dtype=torch.bool);active[pred['active'][0].topk(min(node_count,len(active))).indices]=True
        odds=torch.logsumexp(pred['kind'][0,:,:-1],-1)-pred['kind'][0,:,-1];selected=torch.zeros_like(odds,dtype=torch.bool);selected[odds.topk(min(component_count,len(odds))).indices]=True
        physical=coordinate_snapshot(pred)['decoded_nodes_mm'][0];errors=(physical[inverse]-t['nodes']*10000).norm(dim=-1)
        refs=t['refs'][cj];valid=refs>=0;destination=inverse[refs.clamp_min(0)];logits=pred['refs'][0,ci]
        unmasked=logits.argmax(-1);masked=logits.clone()
        if int(active.sum())>=MAX_REFS:masked[...,~active]=-float('inf')
        dim=t['kind'][cj]==0
        record={'sample_id':k,'target_nodes':len(t['nodes']),'image_forecast_nodes':node_count,
            'target_components':len(t['kind']),'image_forecast_components':component_count,
            'post_forward_GT_matched_node_median_mm':float(errors.median()),'post_forward_GT_matched_node_mean_mm':float(errors.mean()),
            'GT_matched_node_activity_recall':float(active[inverse].float().mean()),
            'GT_matched_component_rank_recall_before_DIM_filter':float(selected[ci].float().mean()),
            'GT_matched_component_type_accuracy':float((pred['kind'][0,ci].argmax(-1)==t['kind'][cj]).float().mean()),
            'pointer_slot_accuracy_before_active_mask':float((unmasked[valid]==destination[valid]).float().mean()),
            'pointer_slot_accuracy_after_active_mask_before_duplicate_resolution':float((masked.argmax(-1)[valid]==destination[valid]).float().mean()),
            'dimension_digit_sequence_accuracy_under_GT_matching':float((pred['digits'][0,ci[dim]].argmax(-1)==t['digits'][cj[dim]]).all(-1).float().mean()) if dim.any() else None}
        result.append(record);print(json.dumps(record),flush=True)
    write(a.output,{'schema':'train-post-forward-selection-diagnostic/v1','model_sha256':digest(a.snapshot/'model.safetensors'),
        'rows':result,'twenty_accessed':False,'GT_only_after_image_forward':True,'oracle_matching_used':True,
        'real_inference_quality_claim':False,'query_oracle_is_not_a_deployable_fix':True})
if __name__=='__main__':main()
