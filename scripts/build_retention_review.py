"""Show actual TRAIN-only interventions, with fixed and predicted count kept separate."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.vector import svg

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--run',type=Path,required=True,nargs='+');p.add_argument('--experiment',choices=['EXP-047','EXP-048','EXP-049','EXP-050'],default='EXP-047');a=p.parse_args()
    rows=json.loads((a.root/'data/index.json').read_text());conditions=[]
    for file in sorted(file for run in a.run for file in run.glob('*/receipt.json')):
        d=json.loads(file.read_text());conditions.append({'name':d['variant']['name'],'variant':d['variant'],
             'model_sha256':d['model_sha256'],'stopping_reason':d['stopping_reason'],'updates':d['updates'],'exposures':d['exposures'],
             'fixed':d['fixed_final']['groups'],'inferred':d['inferred_final']['groups'],'history':d['history'],
             'path':file.parent.relative_to(a.root).as_posix(),'guard':d.get('guard_summary'),
             'balance':d.get('loss_balance'),'accepted_updates':d.get('accepted_updates',d['updates'])})
    if not conditions:raise ValueError('No completed diagnostic condition')
    for r in rows:
        folder=a.root/'data'/r['sample_id'];g=json.loads((folder/'target.json').read_text(encoding='utf-8'))
        (folder/'target.svg').write_text(svg(g),encoding='utf-8')
    state={'schema':'retention-review/v1','experiment':a.experiment,'rows':rows,'conditions':conditions,'actual_model_only':True,
           'complete_DWG_product_passed':False,'Space_deployed':False,'full_training_executed':False}
    (a.root/'retention-review-state.json').write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
    html='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>EXP-047 · 재현 유지 원인 비교</title>
<style>body{font:15px system-ui;color:#17304c;background:#f4f6fa;margin:18px}h1{font-size:23px}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #d9e0e9;padding:6px;text-align:left;font-size:12px}select,button{font:inherit;padding:7px;margin:4px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.panel{background:white;border:1px solid #d9e0e9;border-radius:8px;padding:10px}.view{height:440px;overflow:hidden;cursor:grab}.view img,.view svg{width:100%;height:100%;object-fit:contain;transform-origin:center}.bad{color:#ac263a}pre{white-space:pre-wrap;background:white;padding:12px}.scroll{overflow:auto;max-height:360px}a{color:#2352aa}</style>
<h1>원래 5개 유지 · 추가 5개 재현 — 단일 조건 비교</h1>
<p>동일 초기 가중치에서 시작한 실제 학습 예측입니다. 정답은 가운데 열에만 표시합니다. 10개 모두 train 사례입니다. 일반화 검증·완성 DWG·배포 성공을 뜻하지 않습니다.</p>
<p id="status"></p><div class="scroll"><table><thead><tr><th>조건</th><th>진단 학습량</th><th>고정 count 원래5</th><th>고정 count 추가5</th><th>이미지 count 원래5</th><th>이미지 count 추가5</th></tr></thead><tbody id="summary"></tbody></table></div>
<select id="variant"></select><select id="case"></select><select id="mode"><option value="fixed">고정 capacity 진단</option><option value="inferred">이미지 예측 count</option></select><button id="reset">뷰 초기화</button>
<div class="grid"><section class="panel"><b>① 실제 준공도면</b><div class="view" id="input"></div></section><section class="panel"><b>② 변경전 CAD에서 추출한 감독 그래프</b><div class="view" id="truth"></div></section><section class="panel"><b>③ 실제 모델 예측</b><div class="view" id="prediction"></div></section></div>
<pre id="metrics"></pre><pre id="intervention"></pre><p id="download"></p><h3>같은 이미지 노출량에서 구조·치수 유지</h3>
<table><thead><tr><th>전체 노출 회수</th><th>optimizer update</th><th>원래5 구조 F1</th><th>원래 치수</th><th>추가5 구조 F1</th><th>추가 치수</th></tr></thead><tbody id="history"></tbody></table>
<p>중간 history는 geometry candidate 검사이며 DXF audit를 수행했다고 표시하지 않습니다. 최종 표와 개별 결과에는 실제 native DXF 검사 결과를 사용합니다. 가운데 열은 추출한 감독 geometry이며 CAD 프로그램의 원본 렌더와 구분합니다. 휠 확대·드래그 이동. 학습량 상한은 수렴 판정이 아닙니다.</p>
<script>let state;const $=id=>document.getElementById(id);const fmt=g=>g?g.passed_cases+'/'+g.cases+' · F1 '+g.structure_f1.toFixed(4)+' · 치수 '+g.dimensions_correct_geometry_and_value+'/'+g.required_dimensions:'해당 없음';
async function load(){state=await(await fetch('retention-review-state.json')).json();$('status').textContent=state.conditions.length+'개 완료 조건 · 본학습/Space 재배포 없음';
state.conditions.forEach((v,i)=>{$('variant').add(new Option(v.name,i));const row=document.createElement('tr');[v.name,v.updates+' updates / '+v.exposures+' images',fmt(v.fixed.original),fmt(v.fixed.additional),fmt(v.inferred.original),fmt(v.inferred.additional)].forEach(t=>{const td=document.createElement('td');td.textContent=t;row.append(td)});$('summary').append(row)});
state.rows.forEach((r,i)=>$('case').add(new Option((r.cohort==='original'?'원래 5개':'추가 5개')+' · '+r.sample_id,i)));const safe=state.conditions.findIndex(v=>v.name==='five-safe-lr');if(safe>=0)$('variant').value=safe;await show()}
async function show(){const v=state.conditions[Number($('variant').value)],r=state.rows[Number($('case').value)],mode=$('mode').value,path=v.path+'/'+mode+'-final/'+r.sample_id;
$('download').textContent='';$('history').innerHTML='';$('input').innerHTML='<img src="data/'+r.sample_id+'/input.png">';$('truth').innerHTML=await(await fetch('data/'+r.sample_id+'/target.svg')).text();$('prediction').textContent='읽는 중';
const response=await fetch(path+'/prediction.svg');if(!response.ok){$('prediction').textContent='이 조건은 해당 사례를 학습/평가하지 않았습니다';$('metrics').textContent='5개 조건은 원래 사례만 포함';return}
$('prediction').innerHTML=await response.text();const m=await(await fetch(path+'/metrics.json')).json();$('metrics').className=m.passed?'':'bad';$('metrics').textContent=(m.passed?'구조·치수·DXF 검사 통과 (train 재현)':'미통과')+'\\n구조 F1 '+m.structure_f1.toFixed(6)+' · component '+m.component_f1.toFixed(6)+' · shared refs '+m.shared_reference_f1.toFixed(6)+'\\n치수 '+m.components.dimension.correct_geometry_and_value+'/'+m.components.dimension.target+' · query N'+m.capacity_nodes+'/C'+m.capacity_components+' · 정답 수보다 capacity 부족: '+m.capacity_below_required+'\\ncheckpoint '+v.model_sha256+'\\n종료 '+v.stopping_reason;
$('download').innerHTML='<a href="'+path+'/prediction.dxf">실제 모델 DXF</a> · <a href="'+path+'/metrics.json">개별 검사 원자료</a> · <a href="'+path+'/raw.svg">제약 적용 전</a>';
$('history').innerHTML='';for(const h of v.history){const g=h.groups.original,n=h.groups.additional;const tr=document.createElement('tr');[h.dose,h.updates,g.structure_f1.toFixed(6),g.dimensions_correct_geometry_and_value+'/'+g.required_dimensions,n?n.structure_f1.toFixed(6):'—',n?n.dimensions_correct_geometry_and_value+'/'+n.required_dimensions:'—'].forEach(x=>{const td=document.createElement('td');td.textContent=x;tr.append(td)});$('history').append(tr)}}
['variant','case','mode'].forEach(id=>$(id).onchange=show);$('reset').onclick=()=>document.querySelectorAll('.view svg').forEach(s=>s.style.transform='');document.querySelectorAll('.view').forEach(v=>{let z=1,x=0,y=0,start=null;v.onwheel=e=>{const s=v.querySelector('svg');if(!s)return;e.preventDefault();z=Math.max(.1,Math.min(30,z*Math.exp(-e.deltaY*.001)));s.style.transform='translate('+x+'px,'+y+'px) scale('+z+')'};v.onpointerdown=e=>{start=[e.clientX-x,e.clientY-y];v.setPointerCapture(e.pointerId)};v.onpointermove=e=>{if(start){x=e.clientX-start[0];y=e.clientY-start[1];const s=v.querySelector('svg');if(s)s.style.transform='translate('+x+'px,'+y+'px) scale('+z+')'}};v.onpointerup=()=>start=null});load();</script></html>'''
    html=html.replace("$('download').textContent='';$('history').innerHTML='';", "$('intervention').textContent=(v.guard?'좌표 guard '+JSON.stringify(v.guard):'좌표 guard 없음')+'\\n'+(v.balance?'loss scale: continuous '+v.balance.continuous_scale+' / categorical '+v.balance.categorical_scale:'loss balance 없음');$('download').textContent='';$('history').innerHTML='';")
    if a.experiment=='EXP-048':
        html=html.replace('EXP-047 · 재현 유지 원인 비교','EXP-048 · 좌표 제한과 loss 균형 비교')
        html=html.replace('원래 5개 유지 · 추가 5개 재현 — 단일 조건 비교','좌표 이동 제한 · loss 균형 — 기존5 유지와 추가5 재현')
        html=html.replace("v.name==='five-safe-lr'","v.name==='guard-and-balance'")
        html=html.replace("<h3>같은 이미지 노출량에서 구조·치수 유지</h3>","<p>좌표 guard: update2mm / 기존5 누적10mm. loss balance: 같은 TRAIN10의 초기 shared gradient로 정한 고정 scale. 최종 native 검사와 원자료를 확인하세요. 조건별 자원 상한이므로 같은 노출량의 history도 함께 비교합니다.</p><h3>같은 이미지 노출량에서 구조·치수 유지</h3>")
    if a.experiment in ('EXP-049','EXP-050'):
        html=html.replace('EXP-047 · 재현 유지 원인 비교',a.experiment+' · 보호된 잔차 컴포넌트 학습')
        html=html.replace('고정 count','공통 query reserve').replace('고정 capacity 진단','공통 query reserve').replace('이미지 예측 count','이미지 active/no-object 선택')
        html=html.replace('고정 count 원래5','query reserve 원래5').replace('이미지 count','active/no-object')
        html=html.replace('동일 초기 가중치에서 시작한 실제 학습 예측입니다.','각 실험 내 동일 초기 가중치에서 시작한 실제 학습 예측입니다. EXP-049는 frozen five-safe base + 조건부 residual입니다.')
        html=html.replace('<h3>같은 이미지 노출량에서 구조·치수 유지</h3>','<p>두 모드는 같은 query reserve와 이미지 기반 객체 선택을 사용합니다. 정답 개수·CAD 조회·case ID routing은 없습니다. 기존5 입력 특징의 보호는 이 10개 train 재현 범위이며 일반화 증명이 아닙니다.</p><h3>동일 조건의 실제 노출량과 구조·치수</h3>')
    (a.root/'retention-review.html').write_text(html,encoding='utf-8')
    print(json.dumps({'conditions':len(conditions),'review':str(a.root/'retention-review.html')}))
if __name__=='__main__':main()
