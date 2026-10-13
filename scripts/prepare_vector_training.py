"""Build reproducible synthetic supervision from released before-state CAD copies."""
from __future__ import annotations
import argparse, collections, concurrent.futures, hashlib, json, sys, tarfile, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.cad import extract, render
from img2dwg.vector import exports

def worker(task):
    root,out,row,size,debug=task
    folder=out/row['sample_id']; folder.mkdir(parents=True,exist_ok=True)
    source=root/'cases'/row['sample_id']/'before.dxf'
    graph=extract(source,row['crop']['bbox'],size)
    if len(graph['components'])<10: raise ValueError('Too few supported components')
    graph['sample_id']=row['sample_id']; graph['group_id']=row['group_id']; graph['split']=row['split']
    graph['source_sha256']=row['cad_target_sha256']
    (folder/'target.json').write_text(json.dumps(graph,ensure_ascii=False),encoding='utf-8')
    render(graph).save(folder/'input.png')
    receipt=exports(graph,folder/'factory') if debug else None
    return {'sample_id':row['sample_id'],'split':row['split'],'group_id':row['group_id'],
            'components':dict(collections.Counter(c['kind'] for c in graph['components'])),
            'factory':receipt,'image_sha256':hashlib.sha256((folder/'input.png').read_bytes()).hexdigest(),
            'target_sha256':hashlib.sha256((folder/'target.json').read_bytes()).hexdigest()}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--size',type=int,default=768); p.add_argument('--limit',type=int,default=0); p.add_argument('--workers',type=int,default=4)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    records=[json.loads(x) for x in (args.dataset/'bundle/records.jsonl').read_text(encoding='utf-8').splitlines()]
    # Calibration/test untouched; no source image/feature matching is rerun.
    records=[x for x in records if x['split'] in ('train','validation')]
    if args.limit: records=records[:args.limit]
    tasks=[(args.dataset,args.output,r,args.size,i<5) for i,r in enumerate(records)]
    good=[]; failed=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(worker,t):t[2]['sample_id'] for t in tasks}
        for f in concurrent.futures.as_completed(futures):
            try: good.append(f.result())
            except Exception as exc: failed.append({'sample_id':futures[f],'error':str(exc)})
            if (len(good)+len(failed))%100==0: print(json.dumps({'prepared':len(good),'failed':len(failed)}),flush=True)
    good.sort(key=lambda r:r['sample_id']); (args.output/'index.json').write_text(json.dumps(good),encoding='utf-8')
    summary={'schema':'img2dwg-synthetic-training/v1','records':len(good),'split':dict(collections.Counter(x['split'] for x in good)),
        'components':dict(sum((collections.Counter(x['components']) for x in good),collections.Counter())),
        'failed':failed,'factory_smokes':[x for x in good if x['factory']],
        'resolution':args.size,'real_images_used_for_coordinate_supervision':False,
        'limitations':['native types verified; layer role candidates are not confirmed semantics','no numeric OCR training','near-family split review pending']}
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with tarfile.open(args.output/'training.tar.gz','w:gz') as archive:
        archive.add(args.output/'index.json',arcname='index.json'); archive.add(args.output/'summary.json',arcname='summary.json')
        for r in good:
            for name in ('input.png','target.json'): archive.add(args.output/r['sample_id']/name,arcname=r['sample_id']+'/'+name)
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__': main()
