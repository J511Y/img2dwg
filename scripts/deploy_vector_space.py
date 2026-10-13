"""Publish only inference code to the project's dedicated private Space."""
import argparse, hashlib, json, shutil
from pathlib import Path
from huggingface_hub import HfApi,get_token,snapshot_download

p=argparse.ArgumentParser(); p.add_argument('--model',default='youjunhyeok/img2dwg-vector-first-v2'); p.add_argument('--space',default='youjunhyeok/img2dwg'); args=p.parse_args()
api=HfApi(); info=api.model_info(args.model); assert info.private
folder=Path(snapshot_download(args.model,revision=info.sha,allow_patterns=['model.safetensors','config.json','receipt.json','manifest.json']))
sha=hashlib.sha256((folder/'model.safetensors').read_bytes()).hexdigest(); receipt=json.loads((folder/'receipt.json').read_text())
assert receipt['status']=='completed' and sha==receipt['model_sha256']
root=Path(__file__).resolve().parents[1]; stage=root/'outputs/vector-first-2026-10-13/space-package'; stage.mkdir(parents=True,exist_ok=True)
for name in ('app.py','requirements.txt','README.md'): shutil.copy2(root/'spaces/img2dwg'/name,stage/name)
(stage/'img2dwg').mkdir(exist_ok=True)
for name in ('__init__.py','model.py','vector.py','inference.py'): shutil.copy2(root/'img2dwg'/name,stage/'img2dwg'/name)
space=api.space_info(args.space); assert space.private
api.add_space_secret(args.space,'HF_TOKEN',get_token())
for name,value in {'MODEL_REPO':args.model,'MODEL_REVISION':info.sha,'MODEL_SHA256':sha,'TORCH_THREADS':'2'}.items(): api.add_space_variable(args.space,name,value)
commit=api.upload_folder(repo_id=args.space,repo_type='space',folder_path=stage,ignore_patterns=['__pycache__/**'],commit_message='Deploy trained image-to-vector SVG and editable DXF preview')
out={'space':args.space,'space_url':f'https://huggingface.co/spaces/{args.space}','space_commit':commit.oid,
     'model_repo':args.model,'model_revision':info.sha,'model_sha256':sha,'requested_hardware':'cpu-basic',
     'files':{p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file()},
     'source_dataset_mounted':False,'status':'uploaded-build-pending'}
(root/'outputs/vector-first-2026-10-13/deployment.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out))
