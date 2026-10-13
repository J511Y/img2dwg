"""Public-file hygiene, notebook evidence and deployed artifact verification."""
import hashlib,json,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]; run=root/'outputs/vector-first-2026-10-13'
names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=root,text=True,encoding='utf-8').splitlines()
patterns=[r'\bhf_[A-Za-z0-9]{25,}',r'\bgh[pousr]_[A-Za-z0-9]{25,}',r'\bsk-[A-Za-z0-9_-]{25,}',r'\\\\(?:192\.168\.|10\.\d+\.)']
violations=[]; parsed=0; links=0
for name in names:
    path=root/name
    if path.suffix in ('.dwg','.dxf','.png','.jpg','.jpeg','.safetensors','.pt'): violations.append(name)
    if path.is_file() and path.suffix in ('.py','.json','.md','.txt','.yml','.yaml'):
        content=path.read_text(encoding='utf-8-sig')
        if any(re.search(pattern,content) for pattern in patterns): violations.append(name)
        if path.suffix=='.json': json.loads(content); parsed+=1
        if path.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',content):
                if re.match(r'(?:https?://|#|app://|hf://|codex://)',target) or '<' in target: continue
                target=target.split('#')[0]
                if not target: continue
                if not (path.parent/target).exists(): raise ValueError(f'Missing documentation link in {name}: {target}')
                links+=1
assert not violations,violations
deployment=json.loads((run/'deployment.json').read_text()); receipt=json.loads((run/'space-verification-final/receipt.json').read_text())
assert deployment['space_commit']==receipt['space_revision']
assert receipt['private'] and len(receipt['cases'])==3
for row in receipt['cases']:
    assert row['model_sha256']==deployment['model_sha256'] and row['dxf_audit_errors']==0
    for info in row['artifact_files'].values(): assert hashlib.sha256(Path(info['path']).read_bytes()).hexdigest()==info['sha256']
manifest=json.loads((run/'evidence-manifest.json').read_text())
for name,digest in manifest['files'].items(): assert hashlib.sha256((run/name).read_bytes()).hexdigest()==digest,name
notebook=run/'research-note/weekly/2026-W42.ipynb'; nb=json.loads(notebook.read_text(encoding='utf-8'))
cells=[c for c in nb['cells'] if c['cell_type']=='code']; assert all(c['execution_count'] for c in cells)
assert not any(o['output_type']=='error' for c in cells for o in c['outputs'])
nb_receipt=json.loads((run/'research-note/assets/weekly/2026-W42/notebook-receipt.json').read_text())
assert hashlib.sha256(notebook.read_bytes()).hexdigest()==nb_receipt['sha256']
result={'status':'passed','public_files':len(names),'parsed_public_json':parsed,'valid_document_links':links,
        'remote_upload_cases':len(receipt['cases']),'notebook_executed_cells':len(cells),'evidence_hashes':len(manifest['files'])}
(run/'release-check.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result))
