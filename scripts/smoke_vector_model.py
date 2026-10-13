"""One real optimizer update, checking decoder learning and frozen backbone."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from img2dwg.model import VectorModel,loss,decode
from scripts.train_vector import CADData
torch.set_num_threads(4); torch.manual_seed(20261013)
root=Path('outputs/vector-first-2026-10-13/supervision-smoke-02')
rows=json.loads((root/'index.json').read_text()); data=CADData(root,rows,size=128)
image,target=data[0]; model=VectorModel(); model.train()
encoder_before=model.encoder.embeddings.patch_embeddings.weight.detach().clone()
head_before=model.coords.weight.detach().clone()
pred=model(image[None]); total,details=loss(pred,{k:v[None] for k,v in target.items()})
total.backward(); norm=torch.nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad),5.)
opt=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=.001); opt.step()
result={'finite_loss':bool(torch.isfinite(total)),'loss':float(total.detach()),'gradient_norm':float(norm),
        'head_changed':not torch.equal(head_before,model.coords.weight.detach()),
        'backbone_unchanged':torch.equal(encoder_before,model.encoder.embeddings.patch_embeddings.weight.detach()),
        'prediction_shape':list(pred['coords'].shape),'details':details,'resolution':128,'quality_claim':False}
assert result['finite_loss'] and result['head_changed'] and result['backbone_unchanged']
Path('outputs/vector-first-2026-10-13/gradient-smoke.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
