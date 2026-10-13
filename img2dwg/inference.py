"""Load the pinned first checkpoint and predict vectors from uploaded raster pixels."""
import hashlib, json, time
from pathlib import Path
import numpy as np
import torch
from PIL import Image,ImageOps
from safetensors.torch import load_file
from img2dwg.model import VectorModel,decode

def load_checkpoint(folder,expected_sha=None):
    folder=Path(folder); path=folder/'model.safetensors'
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_sha and sha!=expected_sha: raise ValueError('Checkpoint hash mismatch')
    config=json.loads((folder/'config.json').read_text())
    model=VectorModel(pretrained=False,backbone_config=config['backbone_config'],slots=config.get('slots',1))
    model.load_state_dict(load_file(str(path)),strict=True); model.eval()
    return model,config,sha

def normalize_image(image,size):
    image=ImageOps.exif_transpose(image)
    if 'A' in image.getbands():
        base=Image.new('RGBA',image.size,'white'); image=Image.alpha_composite(base,image.convert('RGBA'))
    image=image.convert('RGB')
    original=image.size; fitted=ImageOps.contain(image,(size-48,size-48),Image.Resampling.LANCZOS)
    offset=((size-fitted.width)//2,(size-fitted.height)//2)
    canvas=Image.new('RGB',(size,size),'white'); canvas.paste(fitted,offset)
    return canvas,{'original_size':original,'fitted_size':fitted.size,'offset':offset,'exif_orientation_applied':True}

@torch.inference_mode()
def predict(model,config,image,threshold=None,width_mm=0.,model_sha=None):
    start=time.perf_counter(); canvas,transform=normalize_image(image,config['size'])
    tensor=torch.from_numpy(np.asarray(canvas,dtype=np.float32).transpose(2,0,1).copy()/255)[None]
    graph=decode(model(tensor),config['size'],config['threshold'] if threshold is None else float(threshold))
    if width_mm and float(width_mm)>0:
        graph['scale']=float(width_mm)/transform['fitted_size'][0]; graph['units']='mm'
        graph['scale_authority']='user-confirmed-width-of-entire-selected-image-crop'
    else: graph['scale_authority']='unknown'
    graph['input_transform']=transform; graph['model_sha256']=model_sha
    graph['normalized_input_pixels_sha256']=hashlib.sha256(canvas.tobytes()).hexdigest()
    graph['elapsed_seconds']=time.perf_counter()-start
    graph['numeric_dimensions_verified']=False
    return graph,canvas
