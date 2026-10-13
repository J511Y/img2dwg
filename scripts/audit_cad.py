"""Audit local CAD handles, separating header HANDSEED hints from entity identities."""
import argparse,collections,contextlib,io,json,logging
from pathlib import Path
import ezdxf


def audit_file(path):
    """Read raw DXF handles without counting HEADER values as entities."""
    lines=path.read_text(encoding='utf-8',errors='replace').splitlines();typ='';section='';var='';handles=[];seed=None;section_name_pending=False;handle_seen=False
    for i in range(0,len(lines)-1,2):
        code,value=lines[i].strip(),lines[i+1].strip()
        if code=='0':
            typ=value
            section_name_pending=value=='SECTION'
            handle_seen=False
        if section_name_pending and code=='2':
            section=value
            section_name_pending=False
        if typ=='ENDSEC':section=''
        if section=='HEADER':
            if code=='9':var=value
            if var=='$HANDSEED' and code=='5':seed=value
        # DIMSTYLE code 5 is an arrow-block NAME; its entity handle is 105.
        elif not handle_seen and ((typ=='DIMSTYLE' and code=='105') or (typ!='DIMSTYLE' and code=='5')) and typ not in ['SECTION','ENDSEC','EOF']:
            handles.append(value)
            handle_seen=True
    counts=collections.Counter(handles)
    stream=io.StringIO();handler=logging.StreamHandler(stream);logger=logging.getLogger('ezdxf');logger.addHandler(handler)
    try:
        with contextlib.redirect_stderr(stream):
            doc=ezdxf.readfile(path);result=doc.audit()
        warnings=stream.getvalue()
    finally:logger.removeHandler(handler)
    return {'duplicate_entity_handle_groups':sum(n>1 for n in counts.values()),'handseed_matches_existing_handle':seed in counts,
            'load_duplicate_handle_warning_count':warnings.count('Found non-unique entity handle'),
            'audit_errors':len(result.errors),'audit_fixes':len(result.fixes),'memory_fixes_saved':False}


def run(root):
    """Audit crop and DWG-reopened local DXFs, without modifying either."""
    rows=[]
    for f in sorted((root/'samples').iterdir()):
        if not (f/'before.dxf').exists():continue
        a=audit_file(f/'before.dxf');b=audit_file(f/'reopened.dxf') if (f/'reopened.dxf').exists() else None
        rows.append({'sample_id':f.name,'dxf_duplicate_handle_groups':a['duplicate_entity_handle_groups'],
                     'audit_errors':a['audit_errors'],'audit_fixes':a['audit_fixes'],
                     'cropped_dxf':a,'dwg_reopened_dxf':b})
    (root/'cad-integrity-audit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print({'audited':len(rows),'entity_duplicate_samples':sum(r['dxf_duplicate_handle_groups']>0 for r in rows),
           'header_handseed_conflicts':sum(r['cropped_dxf']['handseed_matches_existing_handle'] for r in rows),
           'loader_warning_samples':sum(r['cropped_dxf']['load_duplicate_handle_warning_count']>0 for r in rows)})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);run(p.parse_args().root)
