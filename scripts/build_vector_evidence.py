"""Project-local running-week evidence; leaves the central scheduled notes untouched."""
import json,shutil,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]; run=root/'outputs/vector-first-2026-10-13'; work=run/'research-note'; work.mkdir(exist_ok=True)
(work/'projects.json').write_text(json.dumps({'projects':[{'id':'img2dwg','path':str(root)}]}))
(work/'weekly').mkdir(exist_ok=True)
note='# 2026-W42 진행 중 · img2dwg EXP-043 단일 실험 증거\n\n이 문서는 10월 13일의 프로젝트 실험만 기록한 내부 증거 동반본이며 중앙 주간 정기 노트의 대체본이 아니다.\n\n'+(run/'report.md').read_text(encoding='utf-8')
(work/'weekly/2026-W42.md').write_text(note,encoding='utf-8')
evaluation=json.loads((run/'model/evaluation.json').read_text()); pre=json.loads((run/'supervision-v2/summary.json').read_text())
plan={'periods':{'weekly/2026-W42':{
    'metrics':[{'repo':'img2dwg','source_path':'outputs/vector-first-2026-10-13/model/evaluation.json',
        'title':'합성 validation · component coordinate baseline','context':'64 source-identity-separated cases; near-family review pending; 768px threshold .25 one-to-one <=8px; not real/dimension accuracy',
        'columns':['kind','predicted','target','matched','precision','recall','F1'],
        'rows':[[k,v['predicted'],v['target'],v['matched'],v['precision'],v['recall'],v['f1']] for k,v in evaluation['aggregate'].items()],
        'comparability':'single-slot baseline differs in preprocessing/canonicalization/slots; no isolated-effect claim'},
       {'repo':'img2dwg','source_path':'outputs/vector-first-2026-10-13/space-verification-final/receipt.json','title':'인증 실제 업로드/벡터 다운로드 계약',
        'context':'SVG contains no embedded raster; DXF audit; checkpoint SHA propagation. No model accuracy claim.',
        'columns':['case','objects','dxf audit errors'],
        'rows':[[i,r['dxf_entities'],r['dxf_audit_errors']] for i,r in enumerate(json.loads((run/'space-verification-final/receipt.json').read_text())['cases'])]}],
    'images':[]}}}
if (run/'final-preview/comparison.png').exists():
    plan['periods']['weekly/2026-W42']['images'].append({'repo':'img2dwg','path':'outputs/vector-first-2026-10-13/final-preview/comparison.png',
        'caption':'CAD 합성 validation 입력과 실제 모델 예측 · 파생 시각화, 고객 원본 재배포 금지','distribution':'internal-only; no redistribution'})
(work/'asset-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
skill=Path.home()/'.codex/skills/research-note-evidence-assets/scripts'
subprocess.run([sys.executable,str(skill/'build_evidence_bundle.py'),'--workspace',str(work),'--kind','weekly','--period','2026-W42',
                '--start','2026-10-13','--end','2026-10-13','--config',str(work/'asset-plan.json')],check=True)
subprocess.run([sys.executable,str(skill/'build_note_notebook.py'),'--workspace',str(work),'--kind','weekly','--period','2026-W42','--execute'],check=True)
