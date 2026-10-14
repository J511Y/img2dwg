"""Independent model DXF -> DWG -> DXF roundtrip, on copied TRAIN10 outputs.

No source office CAD is converted or changed. CAD UI editing is not claimed.
"""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
import ezdxf
import numpy as np
from scipy.optimize import linear_sum_assignment
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.train_retention_ablation import write

def signature(entity):
    d=entity.dxf;k=entity.dxftype()
    if k=='DIMENSION':return tuple([*d.defpoint,*d.defpoint2,*d.defpoint3,float(entity.get_measurement())])
    if k=='INSERT':return tuple([*d.insert,d.rotation%360,d.xscale,d.yscale,d.zscale])
    if k=='LINE':return tuple([*d.start,*d.end])
    if k=='ARC':return tuple([*d.center,d.radius,d.start_angle%360,d.end_angle%360])
    if k=='CIRCLE':return tuple([*d.center,d.radius])
    raise ValueError(k)

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--converter',type=Path,default=Path('C:/Program Files/ODA/ODAFileConverter 27.1.0/ODAFileConverter.exe'));a=p.parse_args()
    if a.output.exists():raise FileExistsError('Preserve prior roundtrip')
    cases=sorted(a.source.glob('*/prediction.dxf'));assert len(cases)==10
    assert all(json.loads((file.parent/'metrics.json').read_text())['passed'] for file in cases)
    for folder in ['input','dwg','reopened']:(a.output/folder).mkdir(parents=True)
    hashes={}
    for file in cases:
        hashes[file.parent.name]=hashlib.sha256(file.read_bytes()).hexdigest()
        shutil.copy2(file,a.output/'input'/(file.parent.name+'.dxf'))
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=subprocess.SW_HIDE
    for source,dest,kind,pattern in [('input','dwg','DWG','*.dxf'),('dwg','reopened','DXF','*.dwg')]:
        result=subprocess.run([str(a.converter),str((a.output/source).resolve()),str((a.output/dest).resolve()),'ACAD2018',kind,'0','0',pattern],capture_output=True,text=True,timeout=180,startupinfo=startup)
        if result.returncode:raise RuntimeError('ODA conversion failed: '+str(result.returncode))
    checked=[]
    for file in cases:
        key=file.parent.name;original=ezdxf.readfile(file);reopened=ezdxf.readfile(a.output/'reopened'/(key+'.dxf'))
        assert original.units==reopened.units==4 and not reopened.audit().has_errors and not len(reopened.modelspace().query('IMAGE'))
        errors={};counts={}
        for kind in ['DIMENSION','INSERT','LINE','ARC','CIRCLE']:
            before=[signature(e) for e in original.modelspace().query(kind)]
            after=[signature(e) for e in reopened.modelspace().query(kind)]
            assert len(before)==len(after)
            if before:
                one=np.asarray(before);two=np.asarray(after);difference=np.abs(one[:,None]-two[None])
                if kind=='INSERT':difference[...,3]=np.minimum(difference[...,3],360-difference[...,3])
                if kind=='ARC':difference[...,4:6]=np.minimum(difference[...,4:6],360-difference[...,4:6])
                cost=difference.max(-1)
                if kind=='LINE':cost=np.minimum(cost,np.abs(one[:,None]-two[None,:,[3,4,5,0,1,2]]).max(-1))
                ia,ib=linear_sum_assignment(cost);delta=float(cost[ia,ib].max())
            else:delta=0.
            assert delta<1e-5,(key,kind,delta)
            counts[kind]=len(after);errors[kind]=delta
        dwg=a.output/'dwg'/(key+'.dwg');assert dwg.read_bytes()[:6]==b'AC1032'
        assert hashlib.sha256(file.read_bytes()).hexdigest()==hashes[key]
        checked.append({'sample_id':key,'source_prediction_DXF_sha256':hashes[key],'dwg_sha256':hashlib.sha256(dwg.read_bytes()).hexdigest(),
            'reopened_DXF_sha256':hashlib.sha256((a.output/'reopened'/(key+'.dxf')).read_bytes()).hexdigest(),'native_counts':counts,'roundtrip_geometry_max_abs_delta':errors})
    write(a.output/'receipt.json',{'status':'model-output-roundtrip-passed','cases':10,'rows':checked,'DWG_version':'ACAD2018/AC1032',
        'converter_path':str(a.converter),'converter_sha256':hashlib.sha256(a.converter.read_bytes()).hexdigest(),
        'comparison':'one-to-one geometry assignment;LINE endpoints unordered;rotation angles periodic',
        'original_office_files_accessed_or_modified':False,'actual_CAD_UI_open_edit_save':False,'Space_deployed':False})
    print(json.dumps({'cases':10,'native_dimensions':sum(r['native_counts']['DIMENSION'] for r in checked),'status':'passed'}))
if __name__=='__main__':main()
