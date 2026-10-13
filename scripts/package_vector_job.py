import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]; out=root/'outputs/vector-first-2026-10-13/job-code-attempt03'; out.mkdir(parents=True,exist_ok=True)
files=sorted((root/'img2dwg').glob('*.py'))+[root/'scripts/train_vector.py']
with tarfile.open(out/'code.tar.gz','w:gz') as archive:
    for path in files: archive.add(path,arcname=path.relative_to(root).as_posix())
data=root/'outputs/vector-first-2026-10-13/supervision-v2/training.tar.gz'
protocol={'code_sha256':hashlib.sha256((out/'code.tar.gz').read_bytes()).hexdigest(),
          'training_archive_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
          'files':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
          'hardware':'a100-large','timeout_seconds':5400,'max_gpu_cost_usd_at_current_rate':3.75,
          'steps':{'tiny':100,'full':2500},'dataset_uri':'hf://buckets/youjunhyeok/img2dwg/datasets/v0.2-2026-10-13',
          'train_archive_bytes':data.stat().st_size}
(out/'protocol.json').write_text(json.dumps(protocol,indent=2))
(out/'bootstrap.py').write_bytes((root/'scripts/job_vector_bootstrap.py').read_bytes())
print(json.dumps(protocol))
