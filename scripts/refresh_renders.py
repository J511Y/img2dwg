"""Re-render local CAD at a verified exact resolution and refresh registration receipts."""
import argparse,json,sys
from pathlib import Path
import cv2,numpy as np,ezdxf
from ezdxf.addons import odafc
from build_pilot import render,register,digest


def run(root,source_module,converter):
    """Use local snapshots only; registration failures stay explicit."""
    sys.dont_write_bytecode=True;sys.path.insert(0,str(source_module.parent.parent.parent))
    from data_pipeline.dwg_crop import pipeline as crop
    crop.configure_odafc(converter);crop.configure_matplotlib_fonts()
    rows=json.loads((root/'batch-results.json').read_text())
    for index,r in enumerate(rows):
        if r['status']!='extracted_review_pending':continue
        f=root/'samples'/r['sample_id'];rect=crop.Rect(*r['crop']['bbox'])
        r=json.loads((f/'report.json').read_text())
        rows[index]=r
        if r.get('render_resolution_verified'):
            continue
        if not (f/'source.dxf').exists():odafc.readfile(f/'source.dwg',audit=False).saveas(f/'source.dxf')
        if not (f/'reopened.dxf').exists():odafc.readfile(f/'before.dwg',audit=False).saveas(f/'reopened.dxf')
        r['render']=render(ezdxf.readfile(f/'source.dxf'),rect,f/'before-source-render.png')
        render(ezdxf.readfile(f/'reopened.dxf'),rect,f/'cad-render.png')
        a=cv2.imread(str(f/'before-source-render.png'));b=cv2.imread(str(f/'cad-render.png'))
        assert a.shape==b.shape and a.shape[1]==r['render']['width'] and a.shape[0]==r['render']['height']
        r['roundtrip_render_mae']=float(np.abs(a.astype(float)-b.astype(float)).mean())
        r['registration']=register(cv2.imread(str(f/'reference.jpg')),b,f)
        r['render_resolution_verified']=True
        r['artifact_hashes']={p.name:digest(p) for p in f.iterdir() if p.is_file() and p.name not in ['report.json','candidate.json','error.log','worker.log']}
        (f/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        (root/'batch-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'sample':r['sample_id'],'alignment':r['registration']['status'],'render_mae':r['roundtrip_render_mae']}),flush=True)
    (root/'batch-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source-module',type=Path,required=True);p.add_argument('--converter',type=Path,required=True);a=p.parse_args();run(a.root,a.source_module,a.converter)
