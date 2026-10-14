"""Package a ten-case diagnostic; its bootstrap cannot select the full trainer."""
import argparse,hashlib,json,tarfile
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--data-archive',type=Path,required=True);p.add_argument('--release',type=Path,required=True)
    p.add_argument('--remote-data',required=True);p.add_argument('--remote-output',required=True)
    p.add_argument('--suite-minutes',type=float,default=65);p.add_argument('--trial-minutes',type=float,default=4)
    p.add_argument('--comparison-plan');p.add_argument('--trainer',choices=['train_retention_ablation.py','train_guard_balance.py','train_protected_adapter.py'],default='train_retention_ablation.py');a=p.parse_args()
    if a.release.exists():raise FileExistsError('Use a fresh immutable release')
    a.release.mkdir(parents=True)
    with tarfile.open(a.release/'code.tar.gz','w:gz') as arc:
        for path in sorted(Path('img2dwg').glob('*.py')):arc.add(path,arcname=path.as_posix())
        for name in sorted({'train_retention_ablation.py','train_guard_balance.py',a.trainer}):
            arc.add(Path('scripts')/name,arcname='scripts/'+name)
    d={'schema':'img2dwg-retention-release/v1','code_sha256':hashlib.sha256((a.release/'code.tar.gz').read_bytes()).hexdigest(),
       'data_sha256':hashlib.sha256(a.data_archive.read_bytes()).hexdigest(),'data_prefix':a.remote_data,
       'output_prefix':a.remote_output,'suite_minutes':a.suite_minutes,'trial_minutes':a.trial_minutes,
       'comparison_plan':a.comparison_plan,'trainer':a.trainer,'cases':10,
       'full_training_allowed':False,'Space_deployment_allowed':False}
    (a.release/'protocol.json').write_text(json.dumps(d,indent=2))
    script="""import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
root=Path('/mnt/img2dwg');release=root/sys.argv[1];p=json.loads((release/'protocol.json').read_text())
if p['cases']!=10 or p['full_training_allowed'] or p['Space_deployment_allowed']:raise ValueError('Diagnostic scope changed')
subprocess.run([sys.executable,'-m','pip','install','numpy==2.2.6','scipy==1.15.3','pillow==11.3.0','ezdxf==1.4.4','safetensors==0.6.2'],check=True)
work=Path('/tmp/retention-code');data=Path('/tmp/retention-data');work.mkdir();data.mkdir()
for path,key,dest in [(release/'code.tar.gz','code_sha256',work),(root/p['data_prefix'],'data_sha256',data)]:
    if hashlib.sha256(path.read_bytes()).hexdigest()!=p[key]:raise ValueError('Published package changed')
    with tarfile.open(path) as archive:archive.extractall(dest,filter='data')
env=os.environ.copy();env.update(PYTHONUNBUFFERED='1')
trainer=p.get('trainer','train_retention_ablation.py')
if trainer not in ('train_retention_ablation.py','train_guard_balance.py','train_protected_adapter.py'):raise ValueError('Unsupported diagnostic runner')
command=[sys.executable,str(work/'scripts'/trainer),'--data',str(data),
    '--output',str(root/p['output_prefix']),'--suite-minutes',str(p['suite_minutes']),
    '--trial-minutes',str(p['trial_minutes'])]
if p.get('comparison_plan'):command+=['--comparison-plan',str(data/p['comparison_plan'])]
subprocess.run(command,env=env,check=True)
"""
    (a.release/'bootstrap.py').write_text(script)
    print(json.dumps(d))
if __name__=='__main__':main()
