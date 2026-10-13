"""Inspect the user's actual failure and a clearly separate geometry baseline."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from PIL import Image,ImageDraw
from img2dwg.grounding import baseline_graph,assess
from img2dwg.inference import load_checkpoint,predict,normalize_image
from img2dwg.vector import exports
from img2dwg.cad import render
torch.set_num_threads(4)
root=Path('outputs/vector-recovery-2026-10-13'); root.mkdir(exist_ok=True)
image=Image.open(root/'user-failed-input-screenshot-crop.png').convert('RGB')
model,config,sha=load_checkpoint('outputs/vector-first-2026-10-13/model')
old,canvas=predict(model,config,image,model_sha=sha); evidence=assess(old,canvas)
baseline=baseline_graph(canvas); receipt=exports(baseline,root/'observed-baseline')
out=Image.new('RGB',(2304,810),'#eef2f6')
for x,picture in [(0,canvas),(768,render(old)),(1536,render(baseline))]: out.paste(picture,(x,42))
d=ImageDraw.Draw(out)
for x,label in [(10,'Actual screenshot-derived input'),(778,'Rejected trained-coordinate output'),(1546,'Observed line baseline (not model prediction)')]: d.text((x,15),label,fill='black')
out.save(root/'failure-comparison.png')
result={'source':'user screenshot crop;original-upload-resolution-not-available','model_sha256':sha,'failed_model_assessment':evidence,
        'observed_baseline_entities':len(baseline['components']),'baseline_receipt':receipt,'baseline_is_trained_prediction':False}
(root/'failure-assessment.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result))
