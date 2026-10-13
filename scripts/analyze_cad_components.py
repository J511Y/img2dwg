"""Read copied CAD structures without exploding, editing, or saving source documents."""
from __future__ import annotations
import argparse, collections, hashlib, json, logging
from pathlib import Path
import ezdxf


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def counts(entities):
    return dict(collections.Counter(e.dxftype() for e in entities))


def analyze(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    inserts = list(msp.query('INSERT'))
    dimensions = list(msp.query('DIMENSION'))
    reachable, missing, cycles = set(), set(), []

    def visit(name, stack=()):
        if name in stack:
            cycles.append(list(stack) + [name]); return
        if name in reachable: return
        reachable.add(name)
        if name not in doc.blocks:
            missing.add(name); return
        for e in doc.blocks[name]:
            if e.dxftype() == 'INSERT': visit(e.dxf.name, stack + (name,))
            if e.dxftype() == 'DIMENSION' and e.dxf.get('geometry'):
                visit(e.dxf.geometry, stack + (name,))

    for e in inserts: visit(e.dxf.name)
    for e in dimensions:
        if e.dxf.get('geometry'): visit(e.dxf.geometry)
    blocks = []
    for b in doc.blocks:
        if b.name.upper().startswith(('*MODEL_SPACE', '*PAPER_SPACE')): continue
        # Exact storage signature, not a semantic or scale/rotation-invariant match.
        signature = sorted(json.dumps(e.dxfattribs(drop={'handle', 'owner'}), sort_keys=True,
                                      default=str) + '|' + e.dxftype() for e in b)
        blocks.append({'name': b.name, 'entity_count': len(b), 'entity_types': counts(b),
                       'direct_modelspace_insert_count': sum(e.dxf.name == b.name for e in inserts),
                       'dimension_picture_reference_count': sum(e.dxf.get('geometry') == b.name for e in dimensions),
                       'reachable_by_insert_or_dimension': b.name in reachable,
                       'is_dimension_picture': b.name.startswith('*D'),
                       'is_anonymous': b.name.startswith('*'),
                       'flags': b.block.dxf.get('flags', 0),
                       'has_extension_dictionary': b.block_record.has_extension_dict,
                       'nested_insert_names': [e.dxf.name for e in b.query('INSERT')],
                       'storage_attribute_signature_sha256': hashlib.sha256('\n'.join(signature).encode()).hexdigest()})
    dimension_records = []
    for e in dimensions:
        try: measurement = e.get_measurement(); error = None
        except Exception as exc: measurement = None; error = str(exc)
        attrs = e.dxfattribs()
        dimension_records.append({'handle': e.dxf.handle, 'layer': e.dxf.layer,
                                  'dimtype': e.dimtype, 'dimstyle': e.dxf.dimstyle,
                                  'geometry_block': e.dxf.get('geometry'),
                                  'picture_block_exists': bool(e.dxf.get('geometry') in doc.blocks),
                                  'measurement': measurement, 'measurement_error': error,
                                  'text_override': e.dxf.get('text', ''),
                                  'definition_points': {k: attrs[k] for k in ['defpoint','defpoint2','defpoint3','defpoint4'] if k in attrs},
                                  'dimstyle_overrides': e.override().dimstyle_attribs,
                                  'reactor_handles': e.get_reactors()})
    layers = {}
    for e in msp:
        record = layers.setdefault(e.dxf.layer, collections.Counter()); record[e.dxftype()] += 1
    groups = [{'name': name, 'member_count': len(group), 'handles': [e.dxf.handle for e in group]}
              for name, group in doc.groups]
    return {'input_sha256': digest(path), 'entity_types': counts(msp),
            'layers': {k: dict(v) for k,v in layers.items()},
            'linetypes': dict(collections.Counter(e.dxf.get('linetype','BYLAYER') for e in msp)),
            'closed_lwpolyline_count': sum(e.closed for e in msp.query('LWPOLYLINE')),
            'hatch_count': len(msp.query('HATCH')), 'blocks': blocks,
            'inserts': [{'handle': e.dxf.handle, 'name': e.dxf.name, 'layer': e.dxf.layer,
                         'insert': e.dxf.insert, 'rotation': e.dxf.rotation,
                         'scale': [e.dxf.xscale,e.dxf.yscale,e.dxf.zscale],
                         'attributes': [{'tag': a.dxf.tag, 'text': a.dxf.text} for a in e.attribs]}
                        for e in inserts],
            'dimensions': dimension_records, 'groups': groups, 'object_types': counts(doc.objects),
            'reachable_missing_blocks': sorted(missing), 'block_cycles': cycles,
            'units': doc.header.get('$INSUNITS'), 'header_dimassoc': doc.header.get('$DIMASSOC'),
            'dimension_styles': {s.dxf.name: s.dxfattribs() for s in doc.dimstyles},
            'mline_styles': {name: style.dxfattribs() for name, style in doc.mline_styles},
            'limits': 'Block definition presence is not an active instance or semantic label. Storage signatures are incomplete geometry fingerprints. DIMASSOC header is not proof of associative relations.'}


def run(samples, output):
    output.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=output/'reader.log', level=logging.WARNING)
    records=[]; aggregate={phase: collections.Counter() for phase in ['source','before','reopened']}
    for folder in sorted(samples.glob('S[0-9][0-9][0-9]')):
        record={'sample_id': folder.name}
        for phase in aggregate:
            path=folder/(phase+'.dxf')
            before=digest(path); stat=path.stat()
            result=analyze(path)
            result['input_unchanged']=before==digest(path) and stat.st_mtime_ns==path.stat().st_mtime_ns and stat.st_size==path.stat().st_size
            record[phase]=result; aggregate[phase].update(result['entity_types'])
        records.append(record)
    report={'schema':'img2dwg-component-inventory/v1','sample_count':len(records),'records':records}
    (output/'inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    summary={'schema':report['schema'],'sample_count':len(records),'phases':{},
             'source_documents_modified':False,'model_training_run':False}
    for phase, total in aggregate.items():
        r=[x[phase] for x in records]
        summary['phases'][phase]={'entity_types':dict(total),
            'files_with_modelspace_insert':sum(bool(x['inserts']) for x in r),
            'files_with_groups':sum(bool(x['groups']) for x in r),
            'block_definition_count':sum(len(x['blocks']) for x in r),
            'reachable_block_definition_count':sum(sum(b['reachable_by_insert_or_dimension'] for b in x['blocks']) for x in r),
            'files_with_missing_reachable_block':sum(bool(x['reachable_missing_blocks']) for x in r),
            'files_with_block_cycles':sum(bool(x['block_cycles']) for x in r),
            'dimension_picture_present':sum(sum(d['picture_block_exists'] for d in x['dimensions']) for x in r),
            'dimension_nondefault_text_override':sum(sum(d['text_override'] not in ['', '<>'] for d in x['dimensions']) for x in r),
            'closed_lwpolyline_count':sum(x['closed_lwpolyline_count'] for x in r),
            'dimassoc_object_count':sum(x['object_types'].get('DIMASSOC',0) for x in r),
            'all_copied_inputs_unchanged':all(x['input_unchanged'] for x in r)}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--samples',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.samples,args.output)
