"""Immutable source/data hash protocol for a bounded shared-graph job."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,required=True);p.add_argument('--data',type=Path,required=True)
    p.add_argument('--prefix',required=True);p.add_argument('--data-prefix',required=True);p.add_argument('--stage',choices=['tiny','full','evaluate'],required=True)
    p.add_argument('--minutes',type=float,required=True);p.add_argument('--output-prefix',required=True);p.add_argument('--resume-prefix');p.add_argument('--initialize-prefix');p.add_argument('--initialize-sha256')
    args=p.parse_args();args.release.mkdir(parents=True,exist_ok=True)
    if (args.release/'protocol.json').exists():raise FileExistsError('Published job protocol is immutable')
    with tarfile.open(args.release/'code.tar.gz','w:gz') as archive:
        for path in sorted(Path('img2dwg').glob('*.py')):archive.add(path,arcname=path.as_posix())
        for name in ('train_shared_graph.py','train_raw_pairs.py'):archive.add(Path('scripts')/name,arcname='scripts/'+name)
    protocol={**vars(args),'release':str(args.release),'data':str(args.data),
              'code_sha256':hashlib.sha256((args.release/'code.tar.gz').read_bytes()).hexdigest(),
              'data_sha256':hashlib.sha256(args.data.read_bytes()).hexdigest()}
    (args.release/'protocol.json').write_text(json.dumps(protocol,indent=2))
    bootstrap='''import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
root=Path('/mnt/img2dwg');release=root/sys.argv[1];p=json.loads((release/'protocol.json').read_text())
subprocess.run([sys.executable,'-m','pip','install','transformers==4.57.6','huggingface-hub==0.36.2','numpy==2.2.6','scipy==1.15.3','pillow==11.3.0','ezdxf==1.4.4','safetensors==0.6.2'],check=True)
code=release/'code.tar.gz';data=root/p['data_prefix']
for path,field in [(code,'code_sha256'),(data,'data_sha256')]:
    if hashlib.sha256(path.read_bytes()).hexdigest()!=p[field]:raise ValueError('Immutable package hash mismatch')
work=Path('/tmp/shared-code');corpus=Path('/tmp/shared-data');work.mkdir();corpus.mkdir()
with tarfile.open(code) as a:a.extractall(work,filter='data')
with tarfile.open(data) as a:a.extractall(corpus,filter='data')
env=os.environ.copy();env.update(PYTHONUNBUFFERED='1',HF_HUB_DISABLE_PROGRESS_BARS='1',CODE_SHA256=p['code_sha256'],TRAINING_ARCHIVE_SHA256=p['data_sha256'])
command=[sys.executable,str(work/'scripts/train_shared_graph.py'),'--data',str(corpus),'--output',str(root/p['output_prefix']),'--stage',p['stage'],'--minutes',str(p['minutes'])]
if p.get('resume_prefix'):command+=['--resume',str(root/p['resume_prefix'])]
if p.get('initialize_prefix'):
    initial=root/p['initialize_prefix']
    if hashlib.sha256(initial.read_bytes()).hexdigest()!=p['initialize_sha256']:raise ValueError('Initial checkpoint changed')
    command+=['--initialize',str(initial)]
subprocess.run(command,env=env,check=True)
'''
    (args.release/'bootstrap.py').write_text(bootstrap)
    print(json.dumps(protocol))
if __name__=='__main__':main()
