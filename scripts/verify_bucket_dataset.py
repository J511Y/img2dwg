"""Read back an uploaded private bucket release and verify every shard and primary pair."""
from __future__ import annotations
import argparse, collections, concurrent.futures, hashlib, json, subprocess, tarfile, time
from pathlib import Path
from prepare_dataset import digest,write_json


def fetch(remote,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run(['hf','buckets','cp',remote,str(dest),'--format','quiet'],capture_output=True,text=True)
    if result.returncode:raise RuntimeError('bucket_readback_failed: '+result.stderr[-500:])


def verify_shard(row,records,prefix,output):
    path=output/row['filename'];fetch(prefix+'/'+row['filename'],path)
    if digest(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise ValueError('remote_shard_hash_or_size_mismatch: '+path.name)
    primary={}
    for sid in row['sample_ids']:
        r=records[sid]
        primary[f'{sid}/source.dwg']=r['dwg_sha256'];primary[f'{sid}/'+r['image_path']]=r['image_sha256']
        primary[f'{sid}/before.dxf']=r['cad_target_sha256'];primary[f'{sid}/native-components.json.gz']=r['component_sha256']
    found=set();case_ids=set()
    with tarfile.open(path,'r:gz') as tar:
        for member in tar:
            if not member.isfile() or member.name.startswith('/') or '..' in Path(member.name).parts:raise ValueError('unsafe_or_nonfile_archive_member')
            case_ids.add(member.name.split('/')[0])
            if member.name in primary:
                h=hashlib.sha256();stream=tar.extractfile(member)
                for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
                if h.hexdigest()!=primary[member.name]:raise ValueError('remote_archive_member_hash_mismatch: '+member.name)
                found.add(member.name)
    if found!=set(primary) or case_ids!=set(row['sample_ids']):raise ValueError('remote_archive_missing_or_extra_cases')
    return {'filename':row['filename'],'sha256':row['sha256'],'bytes':row['bytes'],
            'records':len(case_ids),'primary_artifacts_verified':len(found),'status':'verified-from-remote-readback'}


def verify(args):
    args.output.mkdir(parents=True,exist_ok=True);prefix=args.prefix.rstrip('/');started=time.time()
    for name in ['files-manifest.json','records.jsonl','summary.json','shards.json','provenance.jsonl','README.md']:
        fetch(prefix+'/'+name,args.output/name)
    manifest=json.loads((args.output/'files-manifest.json').read_text(encoding='utf-8'))
    for row in manifest:
        if not row['filename'].endswith('.tar.gz') and digest(args.output/row['filename'])!=row['sha256']:raise ValueError('remote_metadata_hash_mismatch')
    records={r['sample_id']:r for line in (args.output/'records.jsonl').read_text(encoding='utf-8').splitlines() if (r:=json.loads(line))}
    summary=json.loads((args.output/'summary.json').read_text(encoding='utf-8'));shards=json.loads((args.output/'shards.json').read_text(encoding='utf-8'))
    if len(records)!=summary['records'] or len(records)<args.minimum:raise ValueError('remote_record_count_below_contract')
    result=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(verify_shard,row,records,prefix,args.output/'shards') for row in shards]
        for future in concurrent.futures.as_completed(futures):
            result.append(future.result());write_json(args.output/'shard-verification.json',result)
            print(json.dumps({'phase':'remote-verify','shards_done':len(result),'shards_total':len(shards),'records_verified':sum(r['records'] for r in result),'elapsed_s':round(time.time()-started)}),flush=True)
    if sum(x['records'] for x in result)!=len(records):raise ValueError('remote_shard_count_mismatch')
    receipt={'schema':'img2dwg-remote-dataset-verification/v1','bucket_prefix':prefix,'records':len(records),
             'shards':len(result),'all_remote_shard_sha256_verified':True,
             'primary_artifacts_verified':sum(x['primary_artifacts_verified'] for x in result),
             'metadata_sha256_verified':True,'elapsed_s':time.time()-started,
             'limits':'Byte completeness is not model quality, wall semantics, crop semantic approval or approximate layout-family disjointness.'}
    write_json(args.output/'receipt.json',receipt);print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--minimum',type=int,default=1000);p.add_argument('--workers',type=int,default=2);verify(p.parse_args())
