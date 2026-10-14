"""Show CAD-derived assemblies and their parameters, explicitly not ML results."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.vector import svg

root = Path('outputs/raw-pairs-2026-10-14')
receipt = json.loads((root / 'component-factory/receipt.json').read_text())
palette = {'swing_opening': '#cf286b', 'wall_face_pair': '#16846f', 'centerline': '#a86817',
           'rectangular_loop': '#496c9e', 'dimension': '#9948b5', 'unresolved_residual': '#bcc5ce'}
rows = []
for row in receipt['cases']:
    key = row['sample_id']; folder = root / 'component-factory' / key
    graph = json.loads((folder / 'prediction.json').read_text())
    bundle = json.loads((folder / 'assemblies.json').read_text())
    element = ET.fromstring(svg(graph)); geometry = list(element)[1]
    for child, component in zip(list(geometry), graph['components']):
        child.set('data-component', component['component_id'])
        child.set('stroke', palette[component['assembly_kind']])
    element.set('aria-label', '정답 CAD의 컴포넌트 조립 결과 · 모델 예측 아님')
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    (folder / 'components.svg').write_text(ET.tostring(element, encoding='unicode'), encoding='utf-8')
    rows.append({'id': key, 'svg': f'component-factory/{key}/components.svg',
                 'components': bundle['components'], 'summary': row})
page = '''<!doctype html><html lang="ko"><meta charset="utf-8"><title>정답 CAD 컴포넌트 조립 검증</title>
<style>body{font:15px system-ui;margin:24px;color:#213547;background:#f5f7fa}h1{font-size:24px}.notice{padding:16px;background:#fff1db;border:1px solid #efd1a1;border-radius:8px;line-height:1.7}select{font:inherit;padding:8px;max-width:100%;margin:12px 8px 12px 0}.grid{display:grid;grid-template-columns:2fr 1fr;gap:20px}.canvas{height:580px;background:white;border:1px solid #d7dfeb}.canvas svg{width:100%;height:100%}pre{white-space:pre-wrap;font-size:13px;line-height:1.6}section{background:white;padding:16px;border-radius:8px}.legend{line-height:1.8}.selected{stroke-width:5!important}a{color:#234a88}button{font:inherit;padding:8px}</style>
<h1>정답 CAD의 재사용 컴포넌트 조립 검증</h1><p class="notice"><b>모델 예측 화면이 아닙니다.</b> CAD에서 추출한 종류·파라미터·관계로 정답을 다시 조립하는 확인 화면입니다.<br>5개에서 형상과 치수 112개를 보존했습니다. 미분류 잔여 도형이 약 59% 남아 있어 컴포넌트 정답 준비가 완료된 상태는 아닙니다. 새 컴포넌트 모델은 아직 학습하지 않았습니다.</p>
<p><a href="review.html">실패한 모델의 25개 비교 화면으로 돌아가기</a></p><select id="case"></select><select id="component"></select><button id="all">선택 해제</button>
<p id="downloads"></p>
<div class="grid"><div class="canvas" id="drawing"></div><section><div id="summary"></div><h2>선택한 컴포넌트</h2><pre id="params"></pre><p class="legend">분홍: 문짝+회전 원호<br>초록: 벽 중심축+양면+두께<br>갈색: 중심선<br>파랑: 사각 루프 (업무 의미 미확정)<br>보라: 치수<br>회색: 미분류 잔여 도형</p></section></div>
<script>const rows=__ROWS__;const q=s=>document.querySelector(s);let index=0;
q('#case').innerHTML=rows.map((r,i)=>`<option value="${i}">${i+1} · ${r.id}</option>`).join('');
function highlight(){document.querySelectorAll('#drawing [data-component]').forEach(n=>n.classList.toggle('selected',n.getAttribute('data-component')===q('#component').value));const c=rows[index].components.find(x=>x.id===q('#component').value);q('#params').textContent=c?JSON.stringify({kind:c.kind,parameters:c.parameters,anchor_nodes:c.anchor_nodes,semantic_status:c.semantic_status,native_layers:c.native_layers},null,2):'선택 없음';}
async function show(){const r=rows[index];q('#downloads').innerHTML=`<a href="component-oda/dwg/${r.id}.dwg" download>정답 파라미터 조립 DWG · 모델 예측 아님</a> · <a href="component-factory/${r.id}/assemblies.json" download>컴포넌트·파라미터 JSON</a>`;q('#component').innerHTML=r.components.filter(c=>c.kind!=='unresolved_residual').map(c=>`<option value="${c.id}">${c.id} · ${c.kind}</option>`).join('');q('#summary').textContent=`원래 도형 ${r.summary.original_primitives}개 · 묶은 도형 ${r.summary.grouped_members}개 · 미분류 ${r.summary.unresolved_residual_members}개 · 재조립 기하 오차 ${r.summary.max_geometry_error_mm.toExponential(2)}mm`;q('#drawing').innerHTML=await(await fetch(r.svg)).text();const opening=r.components.find(c=>c.kind==='swing_opening');if(opening)q('#component').value=opening.id;highlight();}
q('#case').onchange=e=>{index=Number(e.target.value);show()};q('#component').onchange=highlight;q('#all').onclick=()=>{q('#component').value='';highlight()};show();</script></html>'''
(root / 'component-review.html').write_text(page.replace('__ROWS__', json.dumps(rows, ensure_ascii=False)), encoding='utf-8')
print(json.dumps({'cases': len(rows), 'component_model_trained': False, 'path': str((root / 'component-review.html').resolve())}))
