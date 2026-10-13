"""Publish-ready private tar shards and auditable metadata; no source paths in cloud indexes."""
from __future__ import annotations
import argparse, collections, hashlib, json, tarfile, time
from pathlib import Path
from prepare_dataset import digest,write_json


def group_records(records):
    """Union exact identities/geometry before assigning splits; approximate families remain unknown."""
    parent={r['sample_id']:r['sample_id'] for r in records};seen={}
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for r in records:
        keys=[('image',r['image_sha256']),('dwg',r['dwg_sha256'])]
        if r['geometry_group_sha256']:keys.append(('geometry',r['geometry_group_sha256']))
        for key in keys:
            if key in seen:
                a,b=find(r['sample_id']),find(seen[key]);parent[max(a,b)]=min(a,b)
            else:seen[key]=r['sample_id']
    groups=collections.defaultdict(list)
    for r in records:groups[find(r['sample_id'])].append(r['sample_id'])
    for r in records:
        members=sorted(groups[find(r['sample_id'])]);group=hashlib.sha256('|'.join(members).encode()).hexdigest()[:20]
        number=int(hashlib.sha256(('img2dwg-v02:'+group).encode()).hexdigest()[:8],16)%1000
        r['group_id']=group;r['split']='train' if number<750 else ('validation' if number<850 else ('calibration' if number<900 else 'test'))
        r['grouping_status']='exact-source-identity-or-dihedral-line-geometry; near-family-review-pending'
    return records


def normalize_tarinfo(info):
    info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0;return info


def package(args):
    root=args.root;bundle=root/'bundle';bundle.mkdir(parents=True,exist_ok=True)
    collection={r['sample_id']:r for r in json.loads((root/'collection-results.json').read_text(encoding='utf-8'))}
    processed=json.loads((root/'preprocessing-results.json').read_text(encoding='utf-8'))
    selected=[r for r in processed if r['status']=='preprocessed' and r['crop_auto_supported'] and r['units_preserved'] and r['source_dxf_unchanged']]
    records=[]
    for r in selected:
        c=collection[r['sample_id']];folder=root/'cases'/r['sample_id']
        if not c['originals_unchanged']:continue
        records.append({'sample_id':r['sample_id'],'case_key':c['case_key'],'pair_authority':c['pair_authority'],
            'image_path':c['primary_image']['relative_path'],'image_size':[c['primary_image']['width'],c['primary_image']['height']],
            'exif_orientation':c['primary_image']['exif_orientation'],'image_sha256':c['primary_image']['sha256'],
            'primary_frame_index':0,'image_frame_count':c['primary_image']['frames'],
            'dwg_sha256':c['sources'][0]['sha256'],'exact_pair_sha256':c['exact_pair_sha256'],'dwg_header':c['dwg_header'],
            'source_dxf_sha256':r['source_dxf_sha256'],'cad_target_path':'before.dxf','component_path':'native-components.json.gz',
            'cad_target_sha256':r['artifact_hashes']['before.dxf'],'component_sha256':r['artifact_hashes']['native-components.json.gz'],
            'cad_units':r['source_units'],'crop':r['crop'],'dimension_preservation':r['dimension_preservation'],
            'entity_types':r['entity_types'],'native_component_types':r['native_component_types'],
            'geometry_group_sha256':r['geometry_group_sha256'],'multiple_references':c['multiple_references'],
            'preprocessor_protocol_sha256':r['preprocessor_protocol_sha256'],
            'semantic_component_catalog_complete':False,'image_to_cad_point_matching_supplied':False,
            'prepared_status':'same-case-paired-native-cad-ready; semantic-assembly-preprocessing-pending'})
    if len(records)<args.minimum:raise ValueError(f'prepared_pairs_below_minimum: {len(records)} < {args.minimum}')
    records=group_records(sorted(records,key=lambda x:x['sample_id']))
    aggregate=collections.Counter();component_types=collections.Counter()
    for r in records:aggregate.update(r['entity_types']);component_types.update(r['native_component_types'])
    summary={'schema':'img2dwg-dataset-release/v0.2','date_kst':'2026-10-13','minimum_required':args.minimum,
        'records':len(records),'exact_pair_duplicates_in_release':len(records)-len({r['exact_pair_sha256'] for r in records}),
        'groups':len({r['group_id'] for r in records}),'split_records':dict(collections.Counter(r['split'] for r in records)),
        'split_groups':{split:len({r['group_id'] for r in records if r['split']==split}) for split in ['train','validation','calibration','test']},
        'entity_types':dict(aggregate),'native_component_types':dict(component_types),
        'dimensions_preserved':aggregate['DIMENSION'],'source_files_unchanged':all(collection[r['sample_id']]['originals_unchanged'] for r in records),
        'pair_authority':'user-confirmed-same-work-request-folder','full_image_feature_alignment_required':False,
        'semantic_component_catalog_complete':False,'near_layout_family_grouping_complete':False,'model_training_run':False,
        'collection_success':sum(x['status']=='collected' for x in collection.values()),
        'collection_failures':sum(x['status']!='collected' for x in collection.values()),
        'preprocessing_success':sum(x['status']=='preprocessed' for x in processed),
        'preprocessing_failures':sum(x['status']!='preprocessed' for x in processed),
        'uncertain_crop_quarantine':sum(x['status']=='preprocessed' and not x['crop_auto_supported'] for x in processed)}
    summary['preprocessor_protocol_counts']=dict(collections.Counter(r['preprocessor_protocol_sha256'] for r in records))
    identities=collections.defaultdict(set)
    for r in records:
        for kind in ['image_sha256','dwg_sha256','geometry_group_sha256']:
            if r[kind]:identities[(kind,r[kind])].add(r['split'])
    summary['exact_identity_cross_split_leaks']=sum(len(v)>1 for v in identities.values())
    if summary['exact_pair_duplicates_in_release'] or summary['exact_identity_cross_split_leaks']:raise ValueError('release_identity_leak_or_duplicate')
    with (bundle/'records.jsonl').open('w',encoding='utf-8') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    with (bundle/'provenance.jsonl').open('w',encoding='utf-8') as f:
        for r in records:
            c=collection[r['sample_id']]
            f.write(json.dumps({'sample_id':r['sample_id'],'case_key':c['case_key'],'sources':[{k:x[k] for k in ['role','relative_path','sha256','size','mtime_ns','original_unchanged']} for x in c['sources']]},ensure_ascii=False)+'\n')
    archive_records=[];started=time.time()
    for offset in range(0,len(records),args.shard_size):
        number=offset//args.shard_size;shard=bundle/f'shard-{number:04d}.tar.gz';batch=records[offset:offset+args.shard_size]
        with tarfile.open(shard,'w:gz',compresslevel=3,dereference=True) as tar:
            for r in batch:
                sid=r['sample_id'];folder=root/'cases'/sid
                for name in ['source.dwg','before.dxf','native-components.json.gz','input-preview.jpg',*[x['relative_path'] for x in collection[sid]['sources'] if x['role']=='as-built-reference']]:
                    tar.add(folder/name,arcname=f'{sid}/{name}',recursive=False,filter=normalize_tarinfo)
        sha=digest(shard);archive_records.append({'filename':shard.name,'sha256':sha,'bytes':shard.stat().st_size,'records':len(batch),'sample_ids':[r['sample_id'] for r in batch]})
        for r in batch:r['shard']=shard.name
        print(json.dumps({'phase':'package','shard':number,'records_done':min(offset+args.shard_size,len(records)),'total':len(records),'bytes':shard.stat().st_size,'elapsed_s':round(time.time()-started)}),flush=True)
    with (bundle/'records.jsonl').open('w',encoding='utf-8') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    summary['shards']=len(archive_records);summary['shard_bytes']=sum(r['bytes'] for r in archive_records)
    write_json(bundle/'summary.json',summary);write_json(bundle/'shards.json',archive_records)
    (bundle/'README.md').write_text('# img2dwg private dataset v0.2\n\nSame-request as-built images and before-state CAD, accepted under the user-confirmed pairing rule. Original DWG, raster references, before.dxf and native-components.json.gz are in tar shards. records.jsonl identifies image, CAD target, split and shard. Read images with EXIF orientation; image/CAD pixel matches are not supplied.\n\nNative INSERT/DIMENSION/text types, raw CAD geometry/tags and dependencies are retained. Wall/door/window/space assembly semantics and DIMASSOC target validation are subsequent preprocessing work, not completed labels. Exact source/dihedral geometry groups are split together; near layout-family grouping remains pending. No model training or performance claim. Private use only; do not publish source assets.\n',encoding='utf-8')
    file_manifest=[{'filename':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(bundle.iterdir()) if p.is_file() and p.name!='files-manifest.json']
    write_json(bundle/'files-manifest.json',file_manifest)
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--minimum',type=int,default=1000);p.add_argument('--shard-size',type=int,default=64)
    package(p.parse_args())
