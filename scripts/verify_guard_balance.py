"""Independently inspect downloaded weights, guards, metrics and native DXF.

File checks and coordinate guard compliance do not substitute for CAD quality.
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
import ezdxf
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.cad import render
from scripts.train_guard_balance import variants

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    started=time.monotonic();rows=json.loads((a.root/'data/index.json').read_text());verified=[];models=[]
    done=json.loads((a.run/'receipt.json').read_text());assert done['training_cases']==10 and not done['full_training_executed'] and not done['Space_deployed']
    for v in variants():
        folder=a.run/v['name'];r=json.loads((folder/'receipt.json').read_text());assert r['variant']==v
        assert sha(folder/'model.safetensors')==r['model_sha256'];models.append({'variant':v['name'],'sha256':r['model_sha256']})
        if v['coordinate_guard']:
            guards=json.loads((folder/'guard-history.json').read_text());assert len(guards)==r['guard_summary']['attempts']
            assert sum(g['accepted'] for g in guards)==r['accepted_updates']
            for g in guards:
                if g['accepted']:
                    assert g['measured_step_mm']<=2. and g['measured_original_drift_mm']<=10.
                else:assert g['alpha']==0 and g['optimizer_restored_on_rejection']
        for mode in ['fixed-final','inferred-final']:
            for row in rows:
                folder_case=folder/mode/row['sample_id'];dxf=folder_case/'prediction.dxf';m=json.loads((folder_case/'metrics.json').read_text())
                doc=ezdxf.readfile(dxf);audit=doc.audit();assert int(doc.units)==4 and not audit.errors
                dims=len(doc.modelspace().query('DIMENSION'));assert dims==m['factory']['dimension_count']
                assert not len(doc.modelspace().query('IMAGE'))
                verified.append({'variant':v['name'],'mode':mode,'sample_id':row['sample_id'],
                    'dxf_sha256':sha(dxf),'audit_errors':len(audit.errors),'native_dimensions':dims,'quality_passed':m['passed']})
        for cohort in ['original','additional']:
            group=[r for r in rows if r['cohort']==cohort];sheet=Image.new('RGB',(1536,560*5),'white');draw=ImageDraw.Draw(sheet)
            sources=[]
            for i,row in enumerate(group):
                data=a.root/'data'/row['sample_id'];pred=folder/'fixed-final'/row['sample_id'];metric=json.loads((pred/'metrics.json').read_text())
                sheet.paste(Image.open(data/'input.png').convert('RGB'),(0,i*560+35))
                sheet.paste(render(json.loads((data/'target.json').read_text(encoding='utf-8'))),(512,i*560+35))
                sheet.paste(render(json.loads((pred/'prediction.json').read_text(encoding='utf-8'))),(1024,i*560+35))
                draw.text((5,i*560+8),f"{v['name']} | {row['sample_id']} | INPUT / EXTRACTED GT / MODEL | F1 {metric['structure_f1']:.4f} | DIM {metric['components']['dimension']['correct_geometry_and_value']}/{metric['components']['dimension']['target']} | pass {metric['passed']}",fill='black')
                sources.append({'sample_id':row['sample_id'],'input_sha256':sha(data/'input.png'),'GT_sha256':sha(data/'target.json'),'prediction_sha256':sha(pred/'prediction.json')})
            image=a.root/f"{v['name']}-{cohort}-five.jpg";sheet.save(image)
            (image.with_suffix('.provenance.json')).write_text(json.dumps({'derived_from_actual_run':True,'transformation':'PIL native vector rendering;three 512px columns;five rows;no geometry editing','sources':sources,'image_sha256':sha(image),'redistribution':'prohibited;controlled-internal-only'},indent=2),encoding='utf-8')
    result={'schema':'guard-balance-artifact-verification/v1','status':'passed','DXFs_checked':len(verified),'models_verified':models,
         'rows':verified,'guard_compliance_checked':True,'model_quality_pass_not_implied':True,'elapsed_seconds':time.monotonic()-started}
    (a.root/'artifact-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','DXFs_checked','elapsed_seconds']}))
if __name__=='__main__':main()
