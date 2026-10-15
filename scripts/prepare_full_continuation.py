"""Copy immutable train/development artifacts and cache CPU vision observations.

The separate twenty's labels/images are not opened here. The source dataset and
office folders are never modified. Interrupted feature extraction can resume.
"""
import argparse,json,shutil,sys,time,hashlib,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from transformers import AutoModel
from img2dwg.model import BACKBONE,REVISION
from scripts.train_raw_pairs import features
from scripts.train_retention_ablation import digest,write

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--ten',type=Path,required=True)
    p.add_argument('--verified',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);torch.set_num_threads(6)
    all_rows=json.loads((a.source/'index.json').read_text());ten=json.loads((a.ten/'index.json').read_text());ids={r['sample_id']:r for r in ten}
    rows=[dict(r) for r in all_rows if r['split']=='train' or r['cohort']=='development']
    assert sum(r['split']=='train' for r in rows)==1028 and len(rows)==1044
    assert len(ids)==10 and set(ids)<={r['sample_id'] for r in rows if r['split']=='train'}
    assert not {r['group_id'] for r in rows if r['split']=='train'}&{r['group_id'] for r in all_rows if r['split']=='validation'}
    c=json.loads((a.verified/'config.json').read_text());library=json.loads((a.source/'library.json').read_text(encoding='utf-8'))
    assert library==json.loads((a.ten/'library.json').read_text(encoding='utf-8'))
    source=a.output/'source';source.mkdir(exist_ok=True)
    for name in ['config.json','model.safetensors']:shutil.copy2(a.verified/name,source/name)
    assert digest(source/'model.safetensors')=='6ca23df9d4b2e080c84f2b1b600c68976af8de4daab9247336ba74f742f9f375'
    shutil.copy2(a.ten/'library.json',a.output/'library.json')
    encoder=None;started=time.monotonic()
    for i,r in enumerate(rows):
        k=r['sample_id'];d=a.output/k;d.mkdir(exist_ok=True)
        if k in ids:r['cohort']=ids[k]['cohort']
        for name,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256')]:
            path=a.source/k/name
            assert digest(path)==r[field],(k,name)
            if k in ids:assert r[field]==ids[k][field]
            if not (d/name).exists():shutil.copy2(path,d/name)
            assert digest(d/name)==r[field]
        receipt=d/'feature-receipt.json'
        if k in ids:
            assert digest(a.ten/k/'features.pt')==ids[k]['features_sha256']
            shutil.copy2(a.ten/k/'features.pt',d/'features.pt');r['features_sha256']=digest(d/'features.pt')
            write(receipt,{'input_sha256':r['input_sha256'],'backbone':BACKBONE,'revision':REVISION,'device':'cpu','protected_source_feature_reused':True,'features_sha256':r['features_sha256']})
        elif receipt.exists():
            prior=json.loads(receipt.read_text());assert prior['input_sha256']==r['input_sha256'] and prior['revision']==REVISION
            assert digest(d/'features.pt')==prior['features_sha256'];r['features_sha256']=prior['features_sha256']
        else:
            if encoder is None:
                encoder=AutoModel.from_pretrained(BACKBONE,revision=REVISION).eval();encoder.requires_grad_(False)
            f=features(encoder,d/'input.png','cpu');torch.save(f,d/'features.pt');r['features_sha256']=digest(d/'features.pt')
            write(receipt,{'input_sha256':r['input_sha256'],'backbone':BACKBONE,'revision':REVISION,'device':'cpu','features_sha256':r['features_sha256']})
        if i%25==0 or i==len(rows)-1:print(json.dumps({'cached':i+1,'total':len(rows),'elapsed_seconds':time.monotonic()-started}),flush=True)
    write(a.output/'index.json',rows);write(a.output/'config.json',c)
    write(a.output/'preparation.json',{'schema':'full-continuation-data/v1','train':1028,'development':16,'retention':10,
        'twenty_accessed':False,'test_calibration_accessed':False,'source_model_sha256':digest(source/'model.safetensors'),
        'input_index_sha256':digest(a.source/'index.json'),'training_nodes_max':max(r['nodes'] for r in rows if r['split']=='train'),
        'training_components_max':max(r['component_count'] for r in rows if r['split']=='train'),
        'features':'frozen DINOv3 CPU,512px,16x16; input image only','backbone_revision':REVISION,
        'group_overlap':0,'source_originals_changed':False,'elapsed_seconds':time.monotonic()-started})
    print(json.dumps({'status':'prepared','rows':len(rows)}),flush=True)
if __name__=='__main__':main()
