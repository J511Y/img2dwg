"""GT component DXF/DWG roundtrip, explicitly separate from model quality."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import ezdxf

root = Path('outputs/raw-pairs-2026-10-14')
staging = root / 'component-oda'
rows = json.loads((root / 'component-factory/receipt.json').read_text())['cases']
for name in ('input', 'dwg', 'reopened'):
    (staging / name).mkdir(parents=True, exist_ok=True)
for row in rows:
    key = row['sample_id']
    shutil.copy2(root / 'component-factory' / key / 'prediction.dxf', staging / 'input' / f'{key}.dxf')
converter = Path('C:/Program Files/ODA/ODAFileConverter 27.1.0/ODAFileConverter.exe')
startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = subprocess.SW_HIDE
for source, destination, kind, pattern in [('input', 'dwg', 'DWG', '*.dxf'), ('dwg', 'reopened', 'DXF', '*.dwg')]:
    command = [str(converter), str((staging / source).resolve()), str((staging / destination).resolve()),
               'ACAD2018', kind, '0', '0', pattern]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=180, startupinfo=startup)
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
results = []
for row in rows:
    key = row['sample_id']; a = ezdxf.readfile(staging / 'input' / f'{key}.dxf'); b = ezdxf.readfile(staging / 'reopened' / f'{key}.dxf')
    da, db = list(a.modelspace().query('DIMENSION')), list(b.modelspace().query('DIMENSION'))
    ia, ib = list(a.modelspace().query('INSERT')), list(b.modelspace().query('INSERT'))
    assert len(da) == len(db) and len(ia) == len(ib) and a.units == b.units == 4
    error = max((abs(float(x.get_measurement()) - float(y.get_measurement())) for x, y in zip(da, db)), default=0)
    assert error < .001
    file = staging / 'dwg' / f'{key}.dwg'; assert file.read_bytes()[:6] == b'AC1032'
    results.append({'sample_id': key, 'dimensions': len(db), 'block_instances': len(ib),
                    'dimension_max_change_mm': error, 'dwg_sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
receipt = {'status': 'five-GT-component-ODA-roundtrips-passed', 'model_inference': False,
           'CAD_UI_edit_save_verified': False, 'converter': converter.name, 'cases': results}
(staging / 'receipt.json').write_text(json.dumps(receipt, indent=2)); print(json.dumps(receipt))
