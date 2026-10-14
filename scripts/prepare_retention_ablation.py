"""Freeze ten TRAIN pairs and observation features for a bounded causal diagnostic."""
import argparse,hashlib,json,shutil,sys,tarfile,time
from pathlib import Path
import torch
from transformers import AutoModel
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.graph_decoder import SharedGraphDecoder
from img2dwg.graph_transfer import initialize
from img2dwg.model import BACKBONE,REVISION
from safetensors.torch import save_file
from train_raw_pairs import features

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Ablation inputs must be a fresh snapshot')
    a.output.mkdir(parents=True);data=a.output/'data';data.mkdir()
    rows=json.loads((a.source/'full-data-v3/index.json').read_text());five=[r for r in rows if r['cohort']=='five']
    groups={r['group_id'] for r in five};additional=[]
    candidates=[r for r in rows if r['split']=='train' and r['cohort']!='five' and
                r['group_id'] not in groups and 959<r['nodes']<=1200 and 726<r['component_count']<=950]
    candidates.sort(key=lambda r:hashlib.sha256(('retention-20261014:'+r['sample_id']).encode()).hexdigest())
    for r in candidates:
        if r['group_id'] in groups:continue
        additional.append(r);groups.add(r['group_id'])
        if len(additional)==5:break
    if len(five)!=5 or len(additional)!=5:raise ValueError('Expected exactly five old and five additional TRAIN cases')
    selected=[{**r,'cohort':'original' if r in five else 'additional'} for r in five+additional]
    assert len({r['group_id'] for r in selected})==10
    library=json.loads((a.source/'full-v1-completed/library.json').read_text(encoding='utf-8'))
    config=json.loads((a.source/'full-v1-completed/config.json').read_text(encoding='utf-8'))
    config['diagnostic_fixed_capacity']=[max(r['nodes'] for r in selected)+32,max(r['component_count'] for r in selected)+32]
    for r in selected:
        dest=data/r['sample_id'];dest.mkdir()
        for name,field in [('input.png','input_sha256'),('target.json','target_sha256'),('components.json','components_sha256')]:
            src=a.source/'full-data-v3'/r['sample_id']/name
            if digest(src)!=r[field]:raise ValueError('Input snapshot hash mismatch')
            shutil.copy2(src,dest/name)
    print(json.dumps({'selected_pairs':10,'additional_ids':[r['sample_id'] for r in additional],
                      'fixed_capacity':config['diagnostic_fixed_capacity'],'twenty_used':False}),flush=True)
    torch.set_num_threads(6);torch.manual_seed(20261014)
    model=SharedGraphDecoder(config['nodes'],config['components'],len(config['texts']),hidden=config['hidden'],
        templates=config['templates'],coord_digits=config['coord_digits'],measure_digits=config['measure_digits'],
        adaptive_capacity=True,minimum_nodes=config['minimum_nodes'],minimum_components=config['minimum_components'])
    transfer=initialize(model,a.source/'tiny-v4-final/model.safetensors',{**config,'library':library})
    save_file({k:v.contiguous() for k,v in model.state_dict().items()},str(data/'initializer.safetensors'))
    write(data/'config.json',config);write(data/'library.json',library)
    encoder=AutoModel.from_pretrained(BACKBONE,revision=REVISION).eval();encoder.requires_grad_(False)
    started=time.monotonic()
    for r in selected:
        f=features(encoder,data/r['sample_id']/'input.png','cpu')
        dest=data/r['sample_id']/'features.pt';torch.save(f.cpu(),dest);r['features_sha256']=digest(dest)
        print(json.dumps({'cached_observation':r['sample_id'],'elapsed_seconds':time.monotonic()-started}),flush=True)
    write(data/'index.json',selected)
    write(data/'preparation.json',{'source_checkpoint':transfer,'expanded_initializer_sha256':digest(data/'initializer.safetensors'),
          'cases':10,'all_split_train':True,'twenty_calibration_test_accessed':False,'originals_modified':False,
          'backbone':BACKBONE,'backbone_revision':REVISION,'feature_input':'actual EXIF512;no CAD render or GT in encoder',
          'selection':'hash ordered TRAIN cases with 959<nodes<=1200 and 726<components<=950;capacity stress,not representative validation'})
    with tarfile.open(a.output/'data.tar.gz','w:gz') as arc:
        for path in sorted(data.rglob('*')):
            if path.is_file():arc.add(path,arcname=path.relative_to(data).as_posix())
    write(a.output/'data-package.json',{'sha256':digest(a.output/'data.tar.gz'),'cases':10,'initializer_sha256':digest(data/'initializer.safetensors')})
if __name__=='__main__':main()
