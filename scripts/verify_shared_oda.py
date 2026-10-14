"""Actual Space-output DXF/DWG/DXF roundtrip; never a GT-factory test."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import ezdxf


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--converter', type=Path, default=Path('C:/Program Files/ODA/ODAFileConverter 27.1.0/ODAFileConverter.exe'))
    args = p.parse_args()
    for name in ('input', 'dwg', 'reopened'):
        (args.output / name).mkdir(parents=True, exist_ok=True)
    for name in ('raw', 'rounded'):
        shutil.copy2(args.source / name / 'prediction.dxf', args.output / 'input' / (name + '.dxf'))
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    for src, dst, kind, pattern in [('input', 'dwg', 'DWG', '*.dxf'), ('dwg', 'reopened', 'DXF', '*.dwg')]:
        result = subprocess.run([str(args.converter), str((args.output / src).resolve()),
            str((args.output / dst).resolve()), 'ACAD2018', kind, '0', '0', pattern],
            capture_output=True, text=True, timeout=180, startupinfo=startup)
        if result.returncode:
            raise RuntimeError('ODA converter failed: ' + str(result.returncode))
    results = []
    for name in ('raw', 'rounded'):
        a = ezdxf.readfile(args.output / 'input' / (name + '.dxf'))
        b = ezdxf.readfile(args.output / 'reopened' / (name + '.dxf'))
        da, db = list(a.modelspace().query('DIMENSION')), list(b.modelspace().query('DIMENSION'))
        assert len(da) == len(db) and a.units == b.units == 4
        error = max((abs(float(x.get_measurement()) - float(y.get_measurement())) for x, y in zip(da, db)), default=0)
        assert error < 1e-5
        assert len(a.modelspace().query('INSERT')) == len(b.modelspace().query('INSERT'))
        assert not b.audit().has_errors
        dwg = args.output / 'dwg' / (name + '.dwg')
        assert dwg.read_bytes()[:6] == b'AC1032'
        results.append({'mode': name, 'native_dimensions': len(db), 'native_blocks': len(b.modelspace().query('INSERT')),
            'dimension_roundtrip_max_error_mm': error, 'dwg_sha256': hashlib.sha256(dwg.read_bytes()).hexdigest(),
            'dwg_bytes': dwg.stat().st_size, 'source_model_dxf_sha256': hashlib.sha256((args.source / name / 'prediction.dxf').read_bytes()).hexdigest()})
    receipt = {'status': 'model-output-ODA-roundtrip-passed', 'converter': args.converter.name,
        'actual_CAD_UI_open_edit_save': False, 'direct_Space_DWG_download': False, 'rows': results}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
