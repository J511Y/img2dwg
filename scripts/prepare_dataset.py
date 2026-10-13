"""Resume a private same-case dataset: immutable copies, CAD targets, native components."""
from __future__ import annotations
import argparse, collections, concurrent.futures, gzip, hashlib, json, logging, math
import os, shutil, subprocess, sys, time, traceback, gc
from pathlib import Path
from PIL import Image, ImageOps
import ezdxf


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    temp.replace(path)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def copy_read_only(source, dest):
    """One copy plus independent destination/source checks; never write to source."""
    source=Path(source);initial=source.stat();dest.parent.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256()
    with source.open('rb') as src, dest.open('wb') as dst:
        for b in iter(lambda:src.read(1024*1024),b''):h.update(b);dst.write(b)
    copied=h.hexdigest();after=digest(source);final=source.stat()
    unchanged=(copied==after==digest(dest) and initial.st_size==final.st_size and initial.st_mtime_ns==final.st_mtime_ns)
    if not unchanged:raise ValueError('source_or_copy_changed_during_collection')
    return {'source_path':str(source),'sha256':copied,'size':initial.st_size,
            'mtime_ns':initial.st_mtime_ns,'original_unchanged':unchanged}


def collect_one(candidate, root):
    sid='P'+candidate['case_key'];folder=root/'cases'/sid;receipt=folder/'collection.json'
    if receipt.exists():
        previous=json.loads(receipt.read_text(encoding='utf-8'))
        if previous['status']=='collected' and all((folder/x['relative_path']).exists() and digest(folder/x['relative_path'])==x['sha256'] for x in previous['sources']):return previous
    folder.mkdir(parents=True,exist_ok=True)
    r={'sample_id':sid,'case_key':candidate['case_key'],'pair_authority':'user-confirmed-same-work-request-folder',
       'pair_semantics':'as-built-image-input__before-state-from-before-after-dwg-output','status':'collecting','sources':[]}
    try:
        d=root/'raw_dwgs'/(sid+'.dwg');entry=copy_read_only(candidate['dwg'],d)
        with d.open('rb') as f:header=f.read(6).decode('ascii',errors='replace')
        if not header.startswith('AC10'):raise ValueError('unsupported_or_invalid_dwg_header')
        local=folder/'source.dwg'
        if not local.exists():os.link(d,local)
        entry['relative_path']='source.dwg';entry['role']='cad-source';r['sources'].append(entry);r['dwg_header']=header
        valid=[]
        for n,source in enumerate(candidate['references']):
            dest=folder/'input'/('reference-'+str(n+1).zfill(2)+Path(source).suffix.lower())
            entry=copy_read_only(source,dest);entry['relative_path']=str(dest.relative_to(folder)).replace('\\','/');entry['role']='as-built-reference';r['sources'].append(entry)
            if dest.suffix.lower() not in {'.jpg','.jpeg','.png','.tif','.tiff','.bmp','.webp'}:continue
            try:
                with Image.open(dest) as image:image.verify()
                with Image.open(dest) as image:
                    size=image.size;frames=getattr(image,'n_frames',1);orientation=image.getexif().get(274,1)
                    if min(size)<=0:continue
                    valid.append({'relative_path':entry['relative_path'],'sha256':entry['sha256'],'width':size[0],'height':size[1],
                                  'frames':frames,'exif_orientation':orientation})
            except Exception as exc:entry['image_error']=type(exc).__name__
        if not valid:raise ValueError('no_decodable_raster_reference')
        r['primary_image']=max(valid,key=lambda x:x['width']*x['height']);r['multiple_references']=len(candidate['references'])>1
        with Image.open(folder/r['primary_image']['relative_path']) as im:
            preview=ImageOps.exif_transpose(im).convert('RGB');preview.thumbnail((640,640));preview.save(folder/'input-preview.jpg',quality=85)
        r['exact_pair_sha256']=hashlib.sha256((r['sources'][0]['sha256']+'|'+r['primary_image']['sha256']).encode()).hexdigest()
        r['status']='collected';r['originals_unchanged']=all(x['original_unchanged'] for x in r['sources'])
    except Exception as exc:
        r['status']='collection_failed';r['error_type']=type(exc).__name__;r['error']=str(exc)
    write_json(receipt,r);return r


def collect(args):
    candidates=json.loads(args.discovery.read_text(encoding='utf-8'))['candidates']
    results=[];started=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(collect_one,c,args.root) for c in candidates]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
            if len(results)%50==0:print(json.dumps({'phase':'collect','finished':len(results),'total':len(candidates),'successful':sum(x['status']=='collected' for x in results),'elapsed_s':round(time.time()-started)}),flush=True)
    results.sort(key=lambda x:x['sample_id']);write_json(args.root/'collection-results.json',results)
    exact=collections.defaultdict(list)
    for r in results:
        if r['status']=='collected':exact[r['exact_pair_sha256']].append(r['sample_id'])
    write_json(args.root/'exact-duplicates.json',{k:v for k,v in exact.items() if len(v)>1})
    print(json.dumps({'collected':sum(x['status']=='collected' for x in results),'unique_exact_pairs':len(exact),'failures':sum(x['status']!='collected' for x in results)}),flush=True)


def convert(args):
    args.output.mkdir(parents=True,exist_ok=True)
    startup=None
    if sys.platform=='win32':
        startup=subprocess.STARTUPINFO();startup.dwFlags=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=subprocess.SW_HIDE
    command=[str(args.converter),str(args.input.resolve()),str(args.output.resolve()),'ACAD2018',args.format,'0','0',args.pattern]
    with (args.root/('oda-'+args.format.lower()+'.log')).open('w',encoding='utf-8') as log:
        p=subprocess.Popen(command,stdout=log,stderr=log,startupinfo=startup)
        started=time.time()
        while p.poll() is None:
            time.sleep(10)
            print(json.dumps({'phase':'oda','format':args.format,'outputs':sum(1 for _ in args.output.glob('*.'+args.format.lower())),'elapsed_s':round(time.time()-started)}),flush=True)
    outputs=list(args.output.glob('*.'+args.format.lower()))
    write_json(args.root/('oda-'+args.format.lower()+'-receipt.json'),{'command':command,'returncode':p.returncode,'output_count':len(outputs),'source_documents_modified':False,'elapsed_s':time.time()-started})
    print(json.dumps({'phase':'oda-complete','returncode':p.returncode,'outputs':len(outputs)}),flush=True)


def load_cad_modules(source_module):
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(source_module.parent.parent.parent))
    from data_pipeline.dwg_crop import pipeline as crop
    from data_pipeline.floorplan_model.export_cad_ir import geometry_to_ir, jsonable
    return crop,geometry_to_ir,jsonable


def native_components(doc,geometry_to_ir,jsonable):
    """Native typed roots plus explicit unreviewed assembly candidates; retain every entity."""
    from ezdxf.lldxf.tagwriter import TagCollector
    def raw_tags(entity):
        collector=TagCollector(dxfversion=doc.dxfversion)
        entity.export_dxf(collector)
        return [[tag.code,jsonable(tag.value)] for tag in collector.tags]
    entities=[];components=[];groups=collections.defaultdict(list)
    for entity in doc.modelspace():
        kind=entity.dxftype();handle=entity.dxf.handle;attrs=jsonable(entity.dxfattribs())
        entities.append({'id':handle,'dxftype':kind,'layer':entity.dxf.layer,'dxf':attrs,'geometry':geometry_to_ir(entity),'raw_dxf_tags':raw_tags(entity)})
        if kind=='DIMENSION':
            value=entity.get_measurement()
            components.append({'id':'dimension:'+handle,'type':'native_dimension','members':[handle],
                'parameters':{'dxf':attrs,'measurement':jsonable(value),'display_style':jsonable(entity.override().dimstyle_attribs)},
                'reactors':entity.get_reactors(),'semantic_status':'native_type_verified','measurement_association_status':'not_yet_resolved'})
        elif kind=='INSERT':
            components.append({'id':'insert:'+handle,'type':'native_block_instance','members':[handle],
                'parameters':{**attrs,'attributes':[{'dxf':jsonable(a.dxfattribs()),'raw_dxf_tags':raw_tags(a)} for a in entity.attribs]},'semantic_status':'template_role_unresolved'})
        elif kind in {'TEXT','MTEXT'}:
            components.append({'id':'text:'+handle,'type':'native_text','members':[handle],
                'parameters':{**attrs,'plain_text':entity.plain_text()},'semantic_status':'native_type_verified'})
        elif kind=='MLINE':
            components.append({'id':'mline:'+handle,'type':'native_mline','members':[handle],'parameters':attrs,'semantic_status':'wall_role_candidate'})
        else:groups[(entity.dxf.layer,kind)].append(handle)
    candidates=[{'id':f'layer-type:{i}','type':'unresolved_geometry_assembly','layer':layer,'dxftype':kind,
                 'members':handles,'semantic_status':'unresolved','note':'Layer/type partition is not one semantic object or negative label.'}
                for i,((layer,kind),handles) in enumerate(sorted(groups.items()))]
    blocks=[]
    for b in doc.blocks:
        if b.name.upper().startswith(('*MODEL_SPACE','*PAPER_SPACE')):continue
        blocks.append({'name':b.name,'base_point':jsonable(b.block.dxf.base_point),
            'entities':[{'id':e.dxf.handle,'dxftype':e.dxftype(),'dxf':jsonable(e.dxfattribs()),'geometry':geometry_to_ir(e),'raw_dxf_tags':raw_tags(e)} for e in b]})
    objects=[]
    for e in doc.objects:
        if e.dxftype()=='DIMASSOC':
            objects.append({'id':e.dxf.handle,'dxftype':e.dxftype(),'dxf':jsonable(e.dxfattribs()),
                            'raw_dxf_tags':raw_tags(e),'validation_status':'unresolved'})
    return {'schema':'img2dwg-native-components/v1','entities':entities,'native_components':components,
        'unresolved_geometry_partitions':candidates,'block_definitions':blocks,'dimension_association_objects':objects,
        'tables':{'layers':[jsonable(x.dxfattribs()) for x in doc.layers],
                  'styles':[jsonable(x.dxfattribs()) for x in doc.styles],
                  'dimstyles':[jsonable(x.dxfattribs()) for x in doc.dimstyles]},
        'semantic_component_catalog_complete':False,
        'limits':'Native types and raw geometry are retained. Wall/door/window/space semantics and association targets are preprocessing candidates, not verified labels.'}


def geometry_group(doc):
    """Exact LINE fingerprint up to translation and planar dihedral symmetries."""
    segments=[]
    for e in doc.modelspace():
        if e.dxftype()=='LINE':segments.append([e.dxf.start.x,e.dxf.start.y,e.dxf.end.x,e.dxf.end.y])
    if not segments:return None
    fingerprints=[]
    for swap in [False,True]:
        for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
            transformed=[]
            for x1,y1,x2,y2 in segments:
                if swap:x1,y1,x2,y2=y1,x1,y2,x2
                transformed.append([sx*x1,sy*y1,sx*x2,sy*y2])
            minx=min(min(x[0],x[2]) for x in transformed);miny=min(min(x[1],x[3]) for x in transformed)
            normalized=[sorted([(round(x1-minx,2),round(y1-miny,2)),(round(x2-minx,2),round(y2-miny,2))]) for x1,y1,x2,y2 in transformed]
            fingerprints.append(hashlib.sha256(json.dumps(sorted(normalized),separators=(',',':')).encode()).hexdigest())
    return min(fingerprints)


def preprocess_one(sid,root,source_module,reuse_protocols=()):
    logging.basicConfig(filename=root/('preprocess-worker-'+str(os.getpid())+'.log'),level=logging.WARNING,force=True)
    protocol=hashlib.sha256((digest(Path(__file__))+digest(Path(__file__).with_name('build_pilot.py'))+digest(source_module)
                            +digest(source_module.parent.parent/'floorplan_model'/'export_cad_ir.py')).encode()).hexdigest()
    folder=root/'cases'/sid;receipt=folder/'preprocessing.json'
    if receipt.exists():
        r=json.loads(receipt.read_text(encoding='utf-8'))
        if r['status']=='preprocessed' and r.get('preprocessor_protocol_sha256') in {protocol,*reuse_protocols} and all((folder/n).exists() and digest(folder/n)==h for n,h in r['artifact_hashes'].items()):return r
    r={'sample_id':sid,'status':'preprocessing','feature_alignment_required':False,'pair_authority':'user-confirmed-same-work-request-folder','preprocessor_protocol_sha256':protocol}
    try:
        crop,geometry_to_ir,jsonable=load_cad_modules(source_module)
        original_entity_rect=crop.entity_rect
        rect_cache={}
        def cached_entity_rect(entity):
            key=id(entity)
            if key not in rect_cache:rect_cache[key]=original_entity_rect(entity)
            return rect_cache[key]
        crop.entity_rect=cached_entity_rect
        path=root/'source_dxfs'/(sid+'.dxf')
        if not path.exists():raise ValueError('oda_dxf_missing')
        r['source_dxf_sha256']=digest(path);doc=ezdxf.readfile(path);r['source_units']=doc.header.get('$INSUNITS',0)
        full=crop.layout_rect(doc.modelspace());rect,confidence,reason,anchors=crop.detect_before_crop(doc.modelspace(),full)
        r['crop']={'bbox':rect.to_list(),'confidence':confidence,'reason':reason,'anchors':anchors,
                   'target_scope':'before-plan-panel; exclusive-unit-semantic-boundary-not-yet-inferred'}
        if rect.width<=0 or rect.height<=0:raise ValueError('invalid_before_crop')
        # Record uncertain crop separately, without rejecting the user's case-pair authority.
        r['crop_auto_supported']='fixed_template_inner_frame' in reason and 'left_half_fallback' not in reason
        selection=rect.inflate(max(rect.width,rect.height)*.015)
        expected=[]
        from build_pilot import dimension_snapshot,dimension_compare
        for e in doc.modelspace().query('DIMENSION'):
            er=crop.entity_rect(e)
            if er and er.intersects(selection):expected.append(dimension_snapshot(e))
        # The cropped copy needs a future allocation hint above live handles.
        # Preserve entity identities; only the generated copy's allocation seed changes.
        from ezdxf.tools.handle import HandleGenerator
        doc.entitydb.handles=HandleGenerator(f'{max(int(h,16) for h in doc.entitydb.keys())+1:X}')
        crop.write_cropped_dxf(doc,rect,folder/'before.dxf')
        cropped=ezdxf.readfile(folder/'before.dxf');actual=[dimension_snapshot(e) for e in cropped.modelspace().query('DIMENSION')]
        compare=dimension_compare(expected,actual)
        r['dimension_preservation']={k:v for k,v in compare.items() if k not in ['expected','actual']}
        if compare['status']=='fail':raise ValueError('dimension_changed_during_crop')
        r['dimension_measurement_errors']=sum('measurement_error' in x for x in actual)
        if r['dimension_measurement_errors']:raise ValueError('dimension_measurement_failure')
        ir=native_components(cropped,geometry_to_ir,jsonable)
        with gzip.open(folder/'native-components.json.gz','wt',encoding='utf-8',compresslevel=3) as f:json.dump(ir,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        r['entity_types']=dict(collections.Counter(e.dxftype() for e in cropped.modelspace()))
        r['native_component_types']=dict(collections.Counter(x['type'] for x in ir['native_components']))
        r['dimension_association_object_count']=len(ir['dimension_association_objects'])
        r['geometry_group_sha256']=geometry_group(cropped)
        r['semantic_component_catalog_complete']=False;r['units_preserved']=r['source_units']==cropped.header.get('$INSUNITS',0)
        r['artifact_hashes']={name:digest(folder/name) for name in ['before.dxf','native-components.json.gz']}
        r['source_dxf_unchanged']=r['source_dxf_sha256']==digest(path);r['status']='preprocessed'
    except Exception as exc:
        r['status']='preprocessing_failed';r['error_type']=type(exc).__name__;r['error']=str(exc)
        (folder/'preprocess-error.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        if 'original_entity_rect' in locals():crop.entity_rect=original_entity_rect
    write_json(receipt,r);return r


def preprocess(args):
    logging.basicConfig(filename=args.root/'preprocess.log',level=logging.WARNING)
    collected=[x for x in json.loads((args.root/'collection-results.json').read_text(encoding='utf-8')) if x['status']=='collected']
    # One representative of an exact image+DWG duplicate, not extra augmented samples.
    seen=set();selected=[]
    for x in collected:
        if x['exact_pair_sha256'] not in seen:selected.append(x);seen.add(x['exact_pair_sha256'])
    selected=selected[:args.limit] if args.limit else selected
    started=time.time();results=[]
    for offset in range(0,len(selected),100):
        # Fresh processes bound retained CAD/font memory; existing artifacts stay intact.
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(preprocess_one,x['sample_id'],args.root,args.source_module,args.reuse_protocol) for x in selected[offset:offset+100]]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())
                if len(results)%20==0:
                    write_json(args.root/'preprocessing-results.json',sorted(results,key=lambda x:x['sample_id']))
                    print(json.dumps({'phase':'preprocess','finished':len(results),'total':len(selected),'successful':sum(x['status']=='preprocessed' for x in results),'auto_crop_supported':sum(x.get('crop_auto_supported',False) for x in results),'elapsed_s':round(time.time()-started)}),flush=True)
        gc.collect()
    results.sort(key=lambda x:x['sample_id']);write_json(args.root/'preprocessing-results.json',results)
    print(json.dumps({'preprocessed':sum(x['status']=='preprocessed' for x in results),'auto_crop_supported':sum(x.get('crop_auto_supported',False) for x in results),'failures':sum(x['status']!='preprocessed' for x in results)}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('collect');c.add_argument('--discovery',type=Path,required=True);c.add_argument('--root',type=Path,required=True);c.add_argument('--workers',type=int,default=4)
    c=sub.add_parser('convert');c.add_argument('--root',type=Path,required=True);c.add_argument('--input',type=Path,required=True);c.add_argument('--output',type=Path,required=True);c.add_argument('--converter',type=Path,required=True);c.add_argument('--format',choices=['DXF','DWG'],default='DXF');c.add_argument('--pattern',default='*.dwg')
    c=sub.add_parser('preprocess');c.add_argument('--root',type=Path,required=True);c.add_argument('--source-module',type=Path,required=True);c.add_argument('--workers',type=int,default=4);c.add_argument('--limit',type=int,default=0);c.add_argument('--reuse-protocol',action='append',default=[])
    args=p.parse_args();{'collect':collect,'convert':convert,'preprocess':preprocess}[args.command](args)
