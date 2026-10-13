"""Private qualitative preview; doesn't turn source similarity into an accuracy metric."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from PIL import Image,ImageDraw
from img2dwg.inference import load_checkpoint,predict
from img2dwg.cad import render
from img2dwg.vector import exports

p=argparse.ArgumentParser(); p.add_argument('--checkpoint',type=Path,required=True); p.add_argument('--image',type=Path,required=True); p.add_argument('--output',type=Path,required=True); args=p.parse_args()
torch.set_num_threads(4); model,config,sha=load_checkpoint(args.checkpoint)
image=Image.open(args.image).convert('RGB'); image=image.crop((24,24,image.width-24,image.height-24))
graph,canvas=predict(model,config,image,.25,model_sha=sha); args.output.mkdir(parents=True,exist_ok=True); receipt=exports(graph,args.output)
target=Image.open(args.image).convert('RGB'); pred=render(graph)
comparison=Image.new('RGB',(1536,810),'#e8edf5'); comparison.paste(target,(0,42)); comparison.paste(pred,(768,42))
draw=ImageDraw.Draw(comparison); draw.text((15,15),'CAD synthetic input / ground truth',fill='black'); draw.text((780,15),f"Actual model prediction ({config['completed_steps']} steps)",fill='black')
comparison.save(args.output/'comparison.png'); print(json.dumps({'model_sha256':sha,'components':len(graph['components']),'receipt':receipt,'seconds':graph['elapsed_seconds']}))
