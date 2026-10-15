"""Independent readback, native dimensions and all thirty quality decisions.

This verifies file fidelity separately from model quality. Failed predictions
remain in the denominator and cannot be turned into a deployment approval.
"""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
import numpy as np
from scipy.optimize import linear_sum_assignment
from scripts.train_retention_ablation import write

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def inspect_native(folder):
    graph=json.loads((folder/'prediction.json').read_text(encoding='utf-8'));m=json.loads((folder/'metrics.json').read_text())
    doc=ezdxf.readfile(folder/'prediction.dxf');audit=doc.audit();ms=doc.modelspace()
    assert doc.units==4 and not audit.errors
    assert len(ms)==m['factory']['entities'] and len(ms.query('INSERT'))==m['factory']['block_instances']
    assert not any(e.dxftype() in ('IMAGE','IMAGEDEF','OLEFRAME','PDFUNDERLAY','DWFUNDERLAY') for e in doc.entitydb.values() if e.is_alive)
    assert '<image' not in (folder/'prediction.svg').read_text(encoding='utf-8').lower()
    dims=list(ms.query('DIMENSION'));pred=[c for c in graph['components'] if c['kind']=='dimension']
    assert len(dims)==len(pred)==m['factory']['dimension_count']
    maximum_anchor_delta=0.;maximum_label_geometry_delta=0.
    if dims:
        # Export uses a bottom-left canvas origin, while metric nodes are
        # centered. This is the writer's fixed transform, never a fitted shift.
        points=np.asarray([np.asarray(c['points'])[:2]*np.array([graph['scale'],-graph['scale']])+
                           np.array([0.,graph['canvas'][1]*graph['scale']]) for c in pred])
        native=np.asarray([[list(e.dxf.defpoint2)[:2],list(e.dxf.defpoint3)[:2]] for e in dims])
        geometry=np.minimum(np.linalg.norm(points[:,None]-native[None],axis=-1).max(-1),
                        np.linalg.norm(points[:,None]-native[None,:,::-1],axis=-1).max(-1))
        labels=np.not_equal.outer([str(c['value_text']) for c in pred],[str(e.dxf.text) for e in dims])
        ii,jj=linear_sum_assignment(geometry+labels*1e9);maximum_anchor_delta=float(geometry[ii,jj].max());assert maximum_anchor_delta<1e-5
        for i,j in zip(ii,jj):
            expected=pred[i];entity=dims[j]
            assert str(entity.dxf.text)==str(expected['value_text'])
            maximum_label_geometry_delta=max(maximum_label_geometry_delta,abs(float(entity.get_measurement())-expected['measurement_mm']))
    if m['passed']:assert maximum_label_geometry_delta<=1.
    return {'quality_passed':m['passed'],'native_dimensions':len(dims),'native_block_instances':len(ms.query('INSERT')),
        'native_dimension_anchor_max_delta_mm':maximum_anchor_delta,'native_dimension_label_geometry_max_delta_mm':maximum_label_geometry_delta,
        'files':{name:sha(folder/name) for name in ['prediction.dxf','prediction.svg','prediction.json','shared-graph.json','metrics.json']}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root;gpu=root/'GPU';fresh=root/'CPU-fresh'
    r=json.loads((gpu/'receipt.json').read_text());f=json.loads((fresh/'receipt.json').read_text());freeze=json.loads((gpu/'candidate-freeze.json').read_text())
    protocol=json.loads((root/'release/protocol.json').read_text());manifest=json.loads((gpu/'manifest.json').read_text())
    assert sha(gpu/'model.safetensors')==r['model_sha256']==f['model_sha256']==freeze['model_sha256']
    assert sha(gpu/'config.json')==f['config_sha256']==freeze['config_sha256']
    assert sha(gpu/'frozen-base.safetensors')==r['frozen_base_sha256']=='6ca23df9d4b2e080c84f2b1b600c68976af8de4daab9247336ba74f742f9f375'
    assert manifest['source_code_sha256']==protocol['hashes']['code.tar.gz'] and manifest['data_archive_sha256']==protocol['hashes']['training.tar.gz']
    assert len(set(manifest['train_ids']))==1028 and r['complete_first_pass'] and r['unique_training_exposed']==1028
    guards=json.loads((gpu/'guard-history.json').read_text());assert len(guards)==r['updates'] and sum(g['accepted'] for g in guards)==r['accepted_updates']
    for g in guards:
        if g['accepted']:assert g['measured_step_mm']<=50.
        else:assert g['alpha']==0 and g['optimizer_restored_on_rejection']
    rows=json.loads((fresh/'index.json').read_text());assert len(rows)==30
    expected=json.loads((root/'data-audit/evaluation-index.json').read_text());assert sha(root/'data-audit/evaluation-index.json')==protocol['evaluation_index_sha256']
    assert {r['sample_id'] for r in rows if r['split']=='validation'}=={r['sample_id'] for r in expected}
    train=json.loads((root/'data/index.json').read_text());train=[r for r in train if r['split']=='train']
    assert not {r['input_sha256'] for r in train}&{r['input_sha256'] for r in expected}
    checked=[]
    for row in rows:
        key=row['sample_id'];group='retention' if row['split']=='train' else 'twenty';folder=fresh/(group+'-final')/key;d=fresh/'review-data'/key
        assert sha(d/'input.png')==row['input_sha256'] and sha(d/'target.json')==row['target_sha256']
        checked.append({'sample_id':key,'group':group,**inspect_native(folder)})
    numeric_pass=all(x['quality_passed'] for x in checked)
    write(root/'artifact-verification.json',{'schema':'full-continuation-independent-native-verification/v1','artifact_status':'passed',
        'model_quality_status':'numeric-passed' if numeric_pass else 'failed','model_sha256':r['model_sha256'],'cases':30,'rows':checked,
        'frozen_verified_base_byte_identical':True,'full_training_unique_cases':1028,'current_image_update_guard_checked':True,
        'retention_not_proven_by_empty_guard_original_ids':True,'retention_proof':'frozen base bytes + fresh native ten-case evaluation',
        'evaluation_cohort':'original19 + one pretraining metadata-only pixel-leak replacement','Space_release_allowed':False,
        'direct_visual_inspection_pending':True,'CAD_UI_edit_save_proven':False})
    print(json.dumps({'artifact_status':'passed','numeric_quality_pass':numeric_pass,'DXFs':30,'native_dimensions':sum(x['native_dimensions'] for x in checked)}))
if __name__=='__main__':main()
