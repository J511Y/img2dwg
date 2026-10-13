"""Remove detected outer panel-frame strokes; compact existing verified CAD copies."""
import collections,hashlib,json,sys,tarfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.cad import render
from img2dwg.vector import exports
root=Path('outputs/vector-first-2026-10-13'); source=root/'supervision'; out=root/'supervision-v2'; out.mkdir(exist_ok=True)
records=json.loads((source/'index.json').read_text()); summary=json.loads((source/'summary.json').read_text()); total_removed=0
for i,row in enumerate(records):
    folder=out/row['sample_id']; folder.mkdir(exist_ok=True); graph=json.loads((source/row['sample_id']/'target.json').read_text())
    size=graph['canvas'][0]; good=[]; removed=0
    for c in graph['components']:
        p=np.array(c['points']); d=np.abs(p[1]-p[0]); parallel=min(d)<.1; along_border=(p[:2]<size*.12).all(axis=0).any() or (p[:2]>size*.88).all(axis=0).any()
        if c['kind']=='segment' and max(d)>size*.75 and parallel and along_border:
            removed+=1
        else: good.append(c)
    graph['components']=good; total_removed+=removed
    points=np.concatenate([np.array(c['points']) for c in good]); lo=points.min(0); hi=points.max(0)
    factor=(size-48)/max(hi-lo); shift=(size-(hi-lo)*factor)/2
    for c in good: c['points']=((np.array(c['points'])-lo)*factor+shift).tolist()
    graph['texts']=[(((np.array(p)-lo)*factor+shift).tolist(),t) for p,t in graph.get('texts',[]) if ((np.array(p)>=lo)&(np.array(p)<=hi)).all()]
    graph['scale']/=factor; graph['preprocessing_v2']={'frame_strokes_removed':removed,'compact_from':lo.tolist(),'factor':factor,'semantic_exclusive_unit_approved':False}
    (folder/'target.json').write_text(json.dumps(graph,ensure_ascii=False),encoding='utf-8'); render(graph).save(folder/'input.png')
    row['components']=dict(collections.Counter(c['kind'] for c in good)); row['factory']=exports(graph,folder/'factory') if i<5 else None
    row['image_sha256']=hashlib.sha256((folder/'input.png').read_bytes()).hexdigest(); row['target_sha256']=hashlib.sha256((folder/'target.json').read_bytes()).hexdigest()
summary['components']=dict(sum((collections.Counter(r['components']) for r in records),collections.Counter())); summary['factory_smokes']=[r for r in records if r['factory']]
summary['frame_strokes_removed']=total_removed; summary['preprocessing']='before-panel-border-candidate-removal+uniform-geometry-compaction;not-exclusive-unit-approval'
(out/'index.json').write_text(json.dumps(records)); (out/'summary.json').write_text(json.dumps(summary,indent=2))
with tarfile.open(out/'training.tar.gz','w:gz') as archive:
    for name in ('index.json','summary.json'): archive.add(out/name,arcname=name)
    for r in records:
        for name in ('input.png','target.json'): archive.add(out/r['sample_id']/name,arcname=r['sample_id']+'/'+name)
print(json.dumps({'records':len(records),'frame_strokes_removed':total_removed,'components':summary['components']}))
