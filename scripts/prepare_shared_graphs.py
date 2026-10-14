"""Read-only real raster/native CAD preparation, with a frozen five/twenty cohort."""
import argparse
import collections
import concurrent.futures
import copy
import hashlib
import json
import sys
import tarfile
from pathlib import Path
import ezdxf
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.cad import extract
from img2dwg.inference import normalize_image
from img2dwg.structured import prepare,compile_graph
from img2dwg.vector import exports
from img2dwg.raw_evaluation import evaluate_case


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def compact_with_text(graph):
    size=graph['canvas'][0]; kept=[]
    for c in graph['components']:
        p=np.asarray(c['points']); delta=np.abs(p[1]-p[0]); border=(p[:2]<size*.12).all(0).any() or (p[:2]>size*.88).all(0).any()
        if c['kind']=='segment' and max(delta)>size*.75 and min(delta)<.1 and border: continue
        kept.append(c)
    points=np.concatenate([c['points'] for c in kept]); low,high=points.min(0),points.max(0)
    factor=(size-48)/max(high-low); offset=(size-(high-low)*factor)/2
    for c in kept: c['points']=((np.asarray(c['points'])-low)*factor+offset).tolist()
    texts=[(((np.asarray(p)-low)*factor+offset).tolist(),text) for p,text in graph['texts'] if (np.asarray(p)>=low).all() and (np.asarray(p)<=high).all()]
    graph.update(components=kept,texts=texts,scale=graph['scale']/factor)
    return graph


def one(task):
    row,dataset,out,cohort=task; key=row['sample_id']; source=Path(dataset)/'cases'/key; folder=Path(out)/key; folder.mkdir(exist_ok=True)
    image=source/row['image_path']; cad=source/'before.dxf'
    assert sha(image)==row['image_sha256'] and sha(cad)==row['cad_target_sha256']
    if (folder/'target.json').exists() and (folder/'components.json').exists():
        graph=json.loads((folder/'target.json').read_text(encoding='utf-8'))
    else:graph=compact_with_text(extract(cad,row['crop']['bbox'],512,min_length_pixels=0))
    doc=ezdxf.readfile(cad); layers={e.dxf.handle:e.dxf.layer for e in doc.modelspace() if e.dxf.hasattr('handle')}
    expected=row['dimension_preservation']['actual_count']; supported=sum(c['kind']=='dimension' for c in graph['components'])
    graph['native_dimension_coverage']={'expected':expected,'supported':supported,'missing_or_unsupported':expected-supported}
    graph.update(sample_id=key,split=row['split'],group_id=row['group_id'])
    bundle=json.loads((folder/'components.json').read_text(encoding='utf-8')) if (folder/'components.json').exists() else prepare(graph,layers)
    with Image.open(image) as im:
        im.seek(row.get('primary_frame_index',0)); canvas,transform=normalize_image(im,512); canvas.save(folder/'input.png')
    for name,value in [('target.json',graph),('components.json',bundle)]:
        (folder/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    counts=dict(collections.Counter(c['kind'] for c in bundle['components']))
    members=sum(len(c['members']) for c in bundle['components'] if c['kind']!='unresolved_edge')
    result={'sample_id':key,'split':row['split'],'cohort':cohort,'group_id':row['group_id'],
            'original_image_sha256':row['image_sha256'],'source_cad_sha256':row['cad_target_sha256'],
            'input_sha256':sha(folder/'input.png'),'target_sha256':sha(folder/'target.json'),'components_sha256':sha(folder/'components.json'),
            'image_transform':transform,'component_counts':counts,'nodes':len(bundle['nodes_mm']),'component_count':len(bundle['components']),
            'primitive_count':len(graph['components']),'grouped_members':members,'unresolved_edge_members':counts.get('unresolved_edge',0),
            'native_dimension_coverage':graph['native_dimension_coverage'],'native_texts':len(graph['texts'])}
    if cohort=='five':
        rebuilt=compile_graph(bundle); factory=exports(rebuilt,folder/'factory')
        metric=evaluate_case(rebuilt,graph,factory)
        assert metric['structure_f1']==1. and metric['components']['dimension']['missing_or_incorrect']==0,(key,metric)
        assert factory['audit_errors']==0
        result.update(factory=factory,GT_factory_geometry=metric,model_inference=False)
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cohort',type=Path,required=True); p.add_argument('--full',action='store_true'); p.add_argument('--workers',type=int,default=4)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'index.json').exists(): raise FileExistsError('Immutable preparation already exists')
    old=json.loads(args.cohort.read_text()); five={r['sample_id'] for r in old if r['split']=='train'}; twenty={r['sample_id'] for r in old if r['split']=='validation'}
    records=[json.loads(line) for line in (args.dataset/'bundle/records.jsonl').read_text(encoding='utf-8').splitlines()]
    records=[r for r in records if r['sample_id'] in five|twenty or args.full and r['split'] in ('train','validation')]
    tasks=[(r,str(args.dataset),str(args.output),'five' if r['sample_id'] in five else 'twenty' if r['sample_id'] in twenty else 'main') for r in records]
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(one,tasks):
            results.append(result)
            if len(results)%50==0 or result['cohort']=='five': print(json.dumps({'prepared':len(results),'last':result['sample_id'],'nodes':result['nodes'],'components':result['component_counts']}),flush=True)
    # A fixed sixteen development examples exclude the twenty pilot cases.
    dev=sorted([r for r in results if r['split']=='validation' and r['cohort']!='twenty'],
               key=lambda r:hashlib.sha256(('development-20261014'+r['sample_id']).encode()).hexdigest())[:16]
    dev_ids={r['sample_id'] for r in dev}
    for r in results:
        if r['sample_id'] in dev_ids:r['cohort']='development'
    training=[r for r in results if r['split']=='train']
    texts=sorted({c['parameters']['text'] for r in training for c in json.loads((args.output/r['sample_id']/'components.json').read_text(encoding='utf-8'))['components'] if c['kind']=='text'})
    summary={'schema':'img2dwg-shared-training/v1','input':'real-as-built;EXIF+512-letterbox-only',
             'splits':dict(collections.Counter(r['split'] for r in results)),'cohorts':dict(collections.Counter(r['cohort'] for r in results)),
             'maximum_nodes':max(r['nodes'] for r in training),'maximum_components':max(r['component_count'] for r in training),
             'text_vocabulary':['<unknown>']+texts,'source_originals_unchanged':True,'same_request_pair_authority':True,
             'required_dimensions_missing_or_unsupported':sum(r['native_dimension_coverage']['missing_or_unsupported'] for r in results),
             'business_semantics_complete':False,'no_test_or_calibration_used':True,
             'twenty_used_for_checkpoint_selection':False,'group_overlap':len({r['group_id'] for r in training}&{r['group_id'] for r in results if r['split']=='validation'})}
    (args.output/'index.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with tarfile.open(args.output/'data.tar.gz','w:gz') as archive:
        for name in ('index.json','summary.json'):archive.add(args.output/name,arcname=name)
        for r in results:
            for name in ('input.png','target.json','components.json'):archive.add(args.output/r['sample_id']/name,arcname=r['sample_id']+'/'+name)
    print(json.dumps({k:v for k,v in summary.items() if k!='text_vocabulary'}),flush=True)
if __name__=='__main__':main()
