"""New derivative snapshot: local native templates; train-only inference library."""
import argparse
import collections
import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.structured import supplement_native_templates,compile_graph
from img2dwg.vector import exports
from img2dwg.raw_evaluation import evaluate_case

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if (args.output/'index.json').exists():raise FileExistsError('Derivative snapshot is immutable')
    args.output.mkdir(parents=True,exist_ok=True);rows=json.loads((args.source/'index.json').read_text(encoding='utf-8'))
    summary=json.loads((args.source/'summary.json').read_text(encoding='utf-8'));library={}
    for i,r in enumerate(rows):
        source=args.source/r['sample_id'];folder=args.output/r['sample_id'];folder.mkdir(exist_ok=True)
        graph=json.loads((source/'target.json').read_text(encoding='utf-8'));old=json.loads((source/'components.json').read_text(encoding='utf-8'))
        b=supplement_native_templates(old,graph)
        if r['split']=='train':library.update(b['templates'])
        for name in ('input.png','target.json'):shutil.copy2(source/name,folder/name)
        (folder/'components.json').write_text(json.dumps(b,ensure_ascii=False),encoding='utf-8')
        r.update(nodes=len(b['nodes_mm']),component_count=len(b['components']),component_counts=dict(collections.Counter(c['kind'] for c in b['components'])),
                 components_sha256=hashlib.sha256((folder/'components.json').read_bytes()).hexdigest(),local_native_templates=len(b['templates']))
        if r['cohort']=='five':
            rebuilt=compile_graph(b);factory=exports(rebuilt,folder/'factory');metric=evaluate_case(rebuilt,graph,factory)
            assert metric['structure_f1']==1. and metric['components']['dimension']['missing_or_incorrect']==0
            r.update(factory=factory,GT_factory_geometry=metric)
        if (i+1)%100==0:print(json.dumps({'supplemented':i+1,'training_templates':len(library)}),flush=True)
    train=[r for r in rows if r['split']=='train'];summary.update(maximum_nodes=max(r['nodes'] for r in train),maximum_components=max(r['component_count'] for r in train),
                                                               native_template_library_training_only=True,native_template_count=len(library),maximum_native_template_extent_mm=2500)
    (args.output/'library.json').write_text(json.dumps(library),encoding='utf-8')
    (args.output/'index.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with tarfile.open(args.output/'data.tar.gz','w:gz') as archive:
        for name in ('index.json','summary.json','library.json'):archive.add(args.output/name,arcname=name)
        for r in rows:
            for name in ('input.png','target.json','components.json'):archive.add(args.output/r['sample_id']/name,arcname=r['sample_id']+'/'+name)
    print(json.dumps({k:v for k,v in summary.items() if k!='text_vocabulary'}),flush=True)
if __name__=='__main__':main()
