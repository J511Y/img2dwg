"""New dataset snapshot retaining coincident native DIMENSION instances."""
import argparse
import hashlib
import json
import collections
import shutil
import sys
import tarfile
from pathlib import Path
import ezdxf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.cad import extract
from img2dwg.structured import prepare,supplement_native_templates
from prepare_shared_graphs import compact_with_text

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise FileExistsError('New snapshot required')
    shutil.copytree(args.source,args.output,ignore=shutil.ignore_patterns('data.tar.gz','factory'))
    rows=json.loads((args.output/'index.json').read_text(encoding='utf-8'));summary=json.loads((args.output/'summary.json').read_text(encoding='utf-8'))
    original={r['sample_id']:r for r in map(json.loads,(args.dataset/'bundle/records.jsonl').read_text(encoding='utf-8').splitlines())}
    repaired=[];library=json.loads((args.output/'library.json').read_text(encoding='utf-8'))
    for r in rows:
        if not r['native_dimension_coverage']['missing_or_unsupported']:continue
        key=r['sample_id'];src=args.dataset/'cases'/key/'before.dxf';assert hashlib.sha256(src.read_bytes()).hexdigest()==r['source_cad_sha256']
        g=compact_with_text(extract(src,original[key]['crop']['bbox'],512,min_length_pixels=0));expected=r['native_dimension_coverage']['expected'];actual=sum(c['kind']=='dimension' for c in g['components'])
        assert actual==expected,(key,actual,expected)
        g.update(sample_id=key,split=r['split'],group_id=r['group_id'],native_dimension_coverage={'expected':expected,'supported':actual,'missing_or_unsupported':0})
        doc=ezdxf.readfile(src);layers={e.dxf.handle:e.dxf.layer for e in doc.modelspace() if e.dxf.hasattr('handle')};b=supplement_native_templates(prepare(g,layers),g)
        folder=args.output/key
        for name,value in [('target.json',g),('components.json',b)]:
            (folder/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');r[name.replace('.json','')+'_sha256']=hashlib.sha256((folder/name).read_bytes()).hexdigest()
        r.update(nodes=len(b['nodes_mm']),component_count=len(b['components']),native_dimension_coverage=g['native_dimension_coverage'],
                 component_counts=dict(collections.Counter(c['kind'] for c in b['components'])))
        if r['split']=='train':library.update(b['templates'])
        repaired.append({'sample_id':key,'required_dimensions':actual,'coincident_annotations_preserved':True})
    train=[r for r in rows if r['split']=='train'];summary.update(maximum_nodes=max(r['nodes'] for r in train),maximum_components=max(r['component_count'] for r in train),
                                                               required_dimensions_missing_or_unsupported=0,native_template_count=len(library),dimension_repairs=repaired)
    (args.output/'index.json').write_text(json.dumps(rows,indent=2));(args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');(args.output/'library.json').write_text(json.dumps(library))
    with tarfile.open(args.output/'data.tar.gz','w:gz') as archive:
        for name in ('index.json','summary.json','library.json'):archive.add(args.output/name,arcname=name)
        for r in rows:
            for name in ('input.png','target.json','components.json'):archive.add(args.output/r['sample_id']/name,arcname=r['sample_id']+'/'+name)
    print(json.dumps({'dimensions_missing':0,'repaired':repaired,'train':len(train),'native_templates':len(library)}))
if __name__=='__main__':main()
