"""Five private GT factory DXF→DWG→DXF checks; never modifies source drawings."""
import hashlib,json,shutil,subprocess
from pathlib import Path
import ezdxf
root=Path('outputs/vector-first-2026-10-13'); staging=root/'factory-oda'; source=root/'supervision-v2'
rows=[r for r in json.loads((source/'index.json').read_text()) if r['factory']]
for name in ('input','dwg','reopened'): (staging/name).mkdir(parents=True,exist_ok=True)
for row in rows: shutil.copy2(source/row['sample_id']/'factory/prediction.dxf',staging/'input'/f"{row['sample_id']}.dxf")
converter=Path('C:/Program Files/ODA/ODAFileConverter 27.1.0/ODAFileConverter.exe')
startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=subprocess.SW_HIDE
def convert(src,dst,kind,pattern):
    completed=subprocess.run([str(converter),str(src.resolve()),str(dst.resolve()),'ACAD2018',kind,'0','0',pattern],
        capture_output=True,text=True,timeout=180,startupinfo=startup)
    if completed.returncode: raise RuntimeError(completed.stdout+completed.stderr)
convert(staging/'input',staging/'dwg','DWG','*.dxf'); convert(staging/'dwg',staging/'reopened','DXF','*.dwg')
result=[]
for row in rows:
    key=row['sample_id']; a=ezdxf.readfile(staging/'input'/f'{key}.dxf'); b=ezdxf.readfile(staging/'reopened'/f'{key}.dxf')
    da=list(a.modelspace().query('DIMENSION')); db=list(b.modelspace().query('DIMENSION'))
    assert len(da)==len(db) and a.units==b.units==4
    errors=[abs(float(x.get_measurement())-float(y.get_measurement())) for x,y in zip(da,db)]
    assert max(errors,default=0)<1e-5
    assert len(a.modelspace().query('INSERT'))==len(b.modelspace().query('INSERT'))
    file=staging/'dwg'/f'{key}.dwg'; assert file.read_bytes()[:6]==b'AC1032'
    result.append({'sample_id':key,'dimensions':len(db),'block_instances':len(b.modelspace().query('INSERT')),
        'dimension_max_error_mm':max(errors,default=0),'dwg_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'dwg_bytes':file.stat().st_size,
        'source_factory_sha256':hashlib.sha256((source/key/'factory/prediction.dxf').read_bytes()).hexdigest(),
        'source_factory_copy_sha256':hashlib.sha256((staging/'input'/f'{key}.dxf').read_bytes()).hexdigest()})
    assert result[-1]['source_factory_sha256']==result[-1]['source_factory_copy_sha256']
receipt={'status':'passed','kind':'GT-factory-ODA-DXF-DWG-DXF;not-model-inference-or-CAD-UI-edit','converter':converter.name,'cases':result}
(staging/'receipt.json').write_text(json.dumps(receipt,indent=2)); print(json.dumps(receipt))
