"""Authenticated real upload/download checks with artifact hash and DXF audits."""
import argparse, hashlib, json, time
from pathlib import Path
import ezdxf
from PIL import Image,ImageOps
from gradio_client import Client,handle_file
from huggingface_hub import HfApi,get_token

p=argparse.ArgumentParser(); p.add_argument('--space',default='youjunhyeok/img2dwg'); p.add_argument('--images',type=Path,nargs='+',required=True)
p.add_argument('--output',type=Path,required=True); args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
info=HfApi().space_info(args.space); assert info.private
client=Client(args.space,hf_token=get_token(),download_files=args.output)
rows=[]
for i,path in enumerate(args.images):
    # PNG intermediary is private; applies EXIF and avoids editor WEBP resampling.
    image=ImageOps.exif_transpose(Image.open(path)); image.convert('RGB').save(args.output/f'upload-{i}.png')
    value=handle_file(str(args.output/f'upload-{i}.png'))
    editor={'background':value,'composite':value,'layers':[]}
    started=time.perf_counter(); result=client.predict(editor,0,.25,api_name='/infer')
    svg_path,dxf_path,json_path,receipt_path=map(Path,result[2:])
    content=svg_path.read_text(encoding='utf-8'); graph=json.loads(json_path.read_text(encoding='utf-8')); receipt=json.loads(receipt_path.read_text())
    assert '<svg' in content and not any(s in content.lower() for s in ['<image','foreignobject','base64'])
    assert graph['geometry_source']=='trained-coordinate-decoder' and graph['model_sha256']==receipt['model_sha256']
    doc=ezdxf.readfile(dxf_path); audit=doc.audit(); assert not audit.has_errors and doc.units==0
    row={'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'uploaded_png_sha256':hashlib.sha256((args.output/f'upload-{i}.png').read_bytes()).hexdigest(),
         'source_protocol':'actual-upload;whole-image-no-manual-exclusive-unit-crop' if i else 'synthetic-upload',
         'wall_seconds':time.perf_counter()-started,'returned_svg_has_embedded_raster':False,
         'component_counts':receipt['component_counts'],'dxf_entities':len(doc.modelspace()),'dxf_audit_errors':len(audit.errors),
         'model_sha256':graph['model_sha256'],'numeric_dimensions_verified':False,
         'artifact_files':{x.name:{'path':str(x),'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in [svg_path,dxf_path,json_path,receipt_path]}}
    rows.append(row); print(json.dumps(row,ensure_ascii=False),flush=True)
result={'status':'passed-upload-to-vector-contract','space':args.space,'space_revision':info.sha,'private':info.private,
        'runtime_stage':str(info.runtime.stage),'cases':rows,'model_quality_or_numeric_dimension_accuracy_proven':False}
(args.output/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
