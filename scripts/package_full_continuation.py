"""Separate train and sealed-evaluation archives; immutable bounded job release."""
import argparse,json,hashlib,tarfile,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--holdout-source',type=Path,required=True)
    p.add_argument('--evaluation-index',type=Path,required=True,help='Metadata-only cohort frozen before training; repairs exact input leakage')
    p.add_argument('--release',type=Path,required=True);p.add_argument('--remote-prefix',required=True);a=p.parse_args()
    if a.release.exists():raise FileExistsError('Immutable release already exists')
    if not a.remote_prefix.startswith('runs/') or '..' in Path(a.remote_prefix).parts:raise ValueError('Fresh runs/ prefix required')
    a.release.mkdir(parents=True);rows=json.loads((a.data/'index.json').read_text());assert len(rows)==1044
    twenty=json.loads(a.evaluation_index.read_text());assert len(twenty)==20 and all(r['split']=='validation' for r in twenty)
    assert not {r['input_sha256'] for r in rows if r['split']=='train'}&{r['input_sha256'] for r in twenty}
    assert not {r['group_id'] for r in rows if r['split']=='train'}&{r['group_id'] for r in twenty}
    with tarfile.open(a.release/'training.tar.gz','w:gz') as arc:
        for f in ['index.json','config.json','preparation.json','library.json','source/config.json','source/model.safetensors']:arc.add(a.data/f,arcname=f)
        for r in rows:
            for f in ['input.png','target.json','components.json','features.pt']:arc.add(a.data/r['sample_id']/f,arcname=r['sample_id']+'/'+f)
    # Copy the already frozen cohort unchanged. Its images/labels are excluded
    # from /tmp/full-training and are extracted only after candidate-freeze.
    with tarfile.open(a.release/'twenty.tar.gz','w:gz') as arc:
        import io
        b=json.dumps(twenty,ensure_ascii=False).encode();info=tarfile.TarInfo('index.json');info.size=len(b);arc.addfile(info,io.BytesIO(b))
        for r in twenty:
            for f in ['input.png','target.json','components.json']:arc.add(a.holdout_source/r['sample_id']/f,arcname=r['sample_id']+'/'+f)
    with tarfile.open(a.release/'code.tar.gz','w:gz') as arc:
        for f in sorted(Path('img2dwg').glob('*.py')):arc.add(f,arcname=f.as_posix())
        for name in ['train_full_continuation.py','evaluate_full_continuation.py','train_retention_ablation.py','train_raw_pairs.py']:
            arc.add(Path('scripts')/name,arcname='scripts/'+name)
    protocol={'schema':'full-continuation-release/v1','train':1028,'development':16,'retention':10,'twenty':20,
        'training_minutes':180,'job_minutes':240,'remote_prefix':a.remote_prefix,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'evaluation_index_sha256':sha(a.evaluation_index),'evaluation_cohort':'existing19 + one pretraining metadata-only pixel-leak replacement',
        'hashes':{f:sha(a.release/f) for f in ['training.tar.gz','twenty.tar.gz','code.tar.gz']},
        'twenty_extracted_only_after_candidate_freeze':True,'Space_automatic_deployment':False}
    (a.release/'protocol.json').write_text(json.dumps(protocol,indent=2))
    bootstrap='''import hashlib,json,os,subprocess,sys,tarfile,time
from pathlib import Path
root=Path('/mnt/img2dwg');release=root/sys.argv[1];p=json.loads((release/'protocol.json').read_text())
subprocess.run([sys.executable,'-m','pip','install','transformers==4.57.6','huggingface-hub==0.36.2','numpy==2.2.6','scipy==1.15.3','pillow==11.3.0','ezdxf==1.4.4','safetensors==0.6.2'],check=True)
for name,expected in p['hashes'].items():
    if hashlib.sha256((release/name).read_bytes()).hexdigest()!=expected:raise ValueError('Published archive hash mismatch')
work=Path('/tmp/full-code');data=Path('/tmp/full-training');work.mkdir();data.mkdir()
for file,dest in [('code.tar.gz',work),('training.tar.gz',data)]:
    with tarfile.open(release/file) as arc:arc.extractall(dest,filter='data')
out=root/p['remote_prefix']/'GPU';env=os.environ.copy();env.update(PYTHONUNBUFFERED='1',HF_HUB_DISABLE_PROGRESS_BARS='1',CODE_SHA256=p['hashes']['code.tar.gz'],TRAINING_ARCHIVE_SHA256=p['hashes']['training.tar.gz'])
subprocess.run([sys.executable,str(work/'scripts/train_full_continuation.py'),'--data',str(data),'--output',str(out),'--minutes',str(p['training_minutes'])],env=env,check=True)
cp=out/'model.safetensors'
frozen={'model_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'frozen_at_unix':time.time(),'config_sha256':hashlib.sha256((out/'config.json').read_bytes()).hexdigest(),'twenty_opened':False}
(out/'candidate-freeze.json').write_text(json.dumps(frozen,indent=2))
twenty=Path('/tmp/frozen-twenty');twenty.mkdir()
with tarfile.open(release/'twenty.tar.gz') as arc:arc.extractall(twenty,filter='data')
subprocess.run([sys.executable,str(work/'scripts/evaluate_full_continuation.py'),'--training-data',str(data),'--twenty-data',str(twenty),'--checkpoint',str(cp),'--output',str(root/p['remote_prefix']/'CPU-fresh')],env=env,check=True)
'''
    (a.release/'bootstrap.py').write_text(bootstrap,encoding='utf-8');print(json.dumps(protocol))
if __name__=='__main__':main()
