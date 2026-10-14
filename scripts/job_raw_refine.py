"""One bounded follow-up triggered by five-case physical geometry failure."""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

root = Path('/mnt/img2dwg')
release = root / 'code/raw-pairs-2026-10-14-attempt02'
protocol = json.loads((release / 'protocol.json').read_text())
subprocess.run([sys.executable, '-m', 'pip', 'install', 'transformers==4.57.6',
               'huggingface-hub==0.36.2', 'numpy==2.2.6', 'scipy==1.15.3',
               'pillow==11.3.0', 'ezdxf==1.4.4', 'safetensors==0.6.2'], check=True)
code = release / 'code.tar.gz'; data = root / 'training/raw-pairs-2026-10-14/pairs.tar.gz'
checkpoint = root / 'runs/raw-pairs-2026-10-14/attempt-01/model.safetensors'
for path, field in [(code, 'code_sha256'), (data, 'data_sha256'), (checkpoint, 'initial_checkpoint_sha256')]:
    assert hashlib.sha256(path.read_bytes()).hexdigest() == protocol[field], 'Pinned artifact mismatch'
work = Path('/tmp/img2dwg-raw-code'); work.mkdir(exist_ok=True)
corpus = Path('/tmp/img2dwg-raw-data'); corpus.mkdir(exist_ok=True)
with tarfile.open(code) as archive:
    archive.extractall(work, filter='data')
with tarfile.open(data) as archive:
    archive.extractall(corpus, filter='data')
env = os.environ.copy()
env.update(PYTHONUNBUFFERED='1', HF_HUB_DISABLE_PROGRESS_BARS='1',
           CODE_SHA256=protocol['code_sha256'], TRAINING_ARCHIVE_SHA256=protocol['data_sha256'])
subprocess.run([sys.executable, str(work / 'scripts/train_raw_pairs.py'), '--data', str(corpus),
               '--output', str(root / 'runs/raw-pairs-2026-10-14/attempt-02'), '--steps', str(protocol['steps']),
               '--lr', '0.00001', '--joint-batch', '--physical-weight', '500', '--freeze-scale',
               '--solve-dimensions', '--resume', str(checkpoint),
               '--model-repo', 'youjunhyeok/img2dwg-raw-five-refine-20261014'], env=env, check=True)
