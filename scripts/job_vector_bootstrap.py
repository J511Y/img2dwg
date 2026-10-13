"""HF Jobs entry point. Dependency installation and a bounded smoke/full run."""
import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
root=Path('/mnt/img2dwg'); release=root/'code/vector-first-2026-10-13-attempt03'
subprocess.run([sys.executable,'-m','pip','install','transformers==4.57.6','huggingface-hub==0.36.2',
               'numpy==2.2.6','scipy==1.15.3','pillow==11.3.0','ezdxf==1.4.4','safetensors==0.6.2'],check=True)
bundle=release/'code.tar.gz'; protocol=json.loads((release/'protocol.json').read_text())
assert hashlib.sha256(bundle.read_bytes()).hexdigest()==protocol['code_sha256']
data=root/'training/vector-first-2026-10-13/training-v2.tar.gz'
assert hashlib.sha256(data.read_bytes()).hexdigest()==protocol['training_archive_sha256']
work=Path('/tmp/img2dwg-code'); work.mkdir(exist_ok=True)
with tarfile.open(bundle) as archive: archive.extractall(work,filter='data')
env=os.environ.copy(); env['PYTHONUNBUFFERED']='1'; env['CODE_SHA256']=protocol['code_sha256']
env['TRAINING_ARCHIVE_SHA256']=protocol['training_archive_sha256']; env['HF_HUB_DISABLE_PROGRESS_BARS']='1'
run=root/'runs/vector-first-2026-10-13/attempt-03'
common=[sys.executable,str(work/'scripts/train_vector.py'),'--data',str(data),'--size','768','--seed','20261013','--slots','4','--canonical-endpoints']
subprocess.run(common+['--output',str(run/'tiny'),'--tiny','5','--steps','100','--batch','2','--eval-records','5'],env=env,check=True)
subprocess.run(common+['--output',str(run/'full'),'--steps','2500','--batch','4','--eval-records','64',
                       '--model-repo','youjunhyeok/img2dwg-vector-first-v2'],env=env,check=True)
