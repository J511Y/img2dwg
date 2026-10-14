"""Create the immutable code/data protocol; no upload or GPU submission here."""
import hashlib
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'outputs/raw-pairs-2026-10-14/job-code'; out.mkdir(parents=True, exist_ok=True)
if (out / 'protocol.json').exists():
    raise RuntimeError('Existing run is frozen. Use a fresh run/prefix instead of overwriting historical packages.')
files = sorted((root / 'img2dwg').glob('*.py')) + [root / 'scripts/train_raw_pairs.py']
with tarfile.open(out / 'code.tar.gz', 'w:gz') as archive:
    for p in files:
        archive.add(p, arcname=p.relative_to(root).as_posix())
data = root / 'outputs/raw-pairs-2026-10-14/data/pairs.tar.gz'
protocol = {'schema': 'img2dwg-raw-five-twenty-protocol/v1',
            'code_sha256': hashlib.sha256((out / 'code.tar.gz').read_bytes()).hexdigest(),
            'data_sha256': hashlib.sha256(data.read_bytes()).hexdigest(),
            'steps': 12000, 'train': 5, 'validation': 20, 'seed': 20261014,
            'flavor': 'a100-large', 'timeout_seconds': 5400, 'cost_rate_usd_hour': 2.50,
            'maximum_job_cost_usd': 3.75, 'cost_rate_verified': 'hf jobs hardware, 2026-10-14',
            'validation_for_training_or_selection': False,
            'source_files': {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(out / 'protocol.json').write_text(json.dumps(protocol, indent=2))
(out / 'bootstrap.py').write_bytes((root / 'scripts/job_raw_bootstrap.py').read_bytes())
print(json.dumps(protocol, indent=2))
