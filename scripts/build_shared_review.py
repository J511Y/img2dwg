"""Local, private comparison of actual model predictions, never GT substitution."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from img2dwg.vector import svg
from img2dwg.cad import render
from PIL import Image,ImageDraw

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--stage',required=True);p.add_argument('--data',type=Path,required=True);args=p.parse_args()
    rows=json.loads((args.data/'index.json').read_text(encoding='utf-8'));chosen=sorted([r for r in rows if r['cohort'] in ('five','twenty')],key=lambda r:(r['cohort']!='five',r['sample_id']))
    for r in chosen:
        folder=args.data/r['sample_id'];g=json.loads((folder/'target.json').read_text(encoding='utf-8'));(folder/'target.svg').write_text(svg(g),encoding='utf-8')
    present=[]
    for r in chosen:
        base=args.root/args.stage/('five-preview' if r['cohort']=='five' else 'twenty-preview')/r['sample_id']
        if not (base/'prediction.json').exists() and r['cohort']=='five':base=args.root/args.stage/'development-preview'/r['sample_id']
        present.append({**r,'prediction':base.relative_to(args.root).as_posix(),'data':(args.data/r['sample_id']).relative_to(args.root).as_posix()})
    state={'stage':args.stage,'rows':present,'actual_model_only':True,'deployment':'unapproved-until-quality-and-direct-inspection-pass'}
    (args.root/'review-state.json').write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
    html=r'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>공유 노드 모델 · 실제 결과 검수</title>
<style>body{font:16px system-ui;background:#f5f7fb;color:#17304c;margin:24px}h1{font-size:24px}button,select{font:inherit;padding:8px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.panel{background:white;border:1px solid #d5deeb;border-radius:8px;padding:12px}.view{height:550px;overflow:hidden;cursor:grab}.view img{width:100%;height:100%;object-fit:contain}.view svg{width:100%;height:100%;transform-origin:center}.label{font-weight:bold;margin:0 0 10px}.bad{color:#a12832}.metrics{white-space:pre-wrap;background:white;padding:16px;margin:12px 0}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #ddd;padding:5px;font-size:13px}</style>
<h1>공유 노드·컴포넌트 모델 — 실제 입력/정답/예측 검수</h1><p id="status"></p>
<p>원본 준공도면을 입력한 모델 예측입니다. 정답 CAD 재조립은 가운데 열에만 표시합니다. 휠 확대·드래그 이동 · 완성 DWG 품질 통과 전 Space 배포 금지</p>
<select id="cases"></select> <button id="prev">이전</button> <button id="next">다음</button> <button id="reset">뷰 초기화</button>
<div class="grid"><section class="panel"><p class="label">① 실제 입력 · 준공도면</p><div class="view" id="input"></div></section><section class="panel"><p class="label">② 정답 · 같은 의뢰 변경전 CAD</p><div class="view" id="truth"></div></section><section class="panel"><p class="label">③ 모델 예측 · 공유 노드 벡터</p><div class="view" id="prediction"></div></section></div>
<div class="metrics" id="metrics"></div><p id="download"></p><h3>필수 치수별 오류 · 숫자와 실제 벡터 길이를 함께 검증</h3><table><thead><tr><th>GT mm</th><th>예측 숫자 mm</th><th>점 위치 오류 mm</th><th>숫자 오류 mm</th><th>실제 길이 오류 mm</th></tr></thead><tbody id="dims"></tbody></table>
<script>let state,rows,index=0;const $=id=>document.getElementById(id);const cache=()=>'?t='+Date.now();
async function load(){state=await (await fetch('review-state.json'+cache())).json();rows=state.rows;$('status').textContent='실행: '+state.stage+' · 검수용 미통과 결과도 그대로 포함';rows.forEach((r,i)=>$('cases').add(new Option((r.cohort==='five'?'5개 train':'별도 20개 pilot')+' · '+r.sample_id,i)));await show()}
async function show(){const r=rows[index];$('cases').value=index;$('input').innerHTML='<img src="'+r.data+'/input.png">';$('truth').innerHTML=await(await fetch(r.data+'/target.svg'+cache())).text();$('prediction').innerHTML='예측 파일 확인 중';$('metrics').textContent='지표 확인 중';$('dims').innerHTML='';try{const response=await fetch(r.prediction+'/prediction.svg'+cache());if(!response.ok)throw Error('아직 예측이 생성되지 않았습니다');$('prediction').innerHTML=await response.text();const m=await(await fetch(r.prediction+'/metrics.json'+cache())).json();$('metrics').className='metrics '+(m.passed?'':'bad');$('metrics').textContent=(m.passed?'수치 검사 통과 (별도 시각·CAD 검수 필요)':'미통과 — 배포 금지')+'\n구조 F1: '+m.structure_f1.toFixed(4)+' · 컴포넌트 F1: '+m.component_f1.toFixed(4)+' · 공유 관계 F1: '+m.shared_reference_f1.toFixed(4)+'\n치수: '+m.components.dimension.correct_geometry_and_value+'/'+m.components.dimension.target+' · 잘못된 반복 노드 참조: '+m.invalid_repeated_node_references+'\n'+(m.export_error||'');$('dims').innerHTML=m.dimension_details.map(d=>'<tr>'+[d.target_value_mm,d.predicted_value_mm,d.max_point_error_mm,d.numeric_error_mm,d.geometry_error_mm].map(v=>'<td>'+Number(v).toFixed(2)+'</td>').join('')+'</tr>').join('');$('download').innerHTML='<a href="'+r.prediction+'/prediction.dxf">모델 DXF</a> · <a href="'+r.prediction+'/shared-graph.json">공유 그래프 JSON</a> · <a href="'+r.prediction+'/raw.svg">제약 적용 전</a>'}catch(e){$('prediction').textContent=e.message;$('metrics').textContent='평가 대기 · 성공 처리하지 않음';$('download').textContent=''}}
$('cases').onchange=()=>{index=Number($('cases').value);show()};$('prev').onclick=()=>{index=(index-1+rows.length)%rows.length;show()};$('next').onclick=()=>{index=(index+1)%rows.length;show()};$('reset').onclick=()=>document.querySelectorAll('.view svg').forEach(s=>s.style.transform='');document.querySelectorAll('.view').forEach(v=>{let z=1,x=0,y=0,start=null;v.onwheel=e=>{const s=v.querySelector('svg');if(!s)return;e.preventDefault();z=Math.max(.1,Math.min(30,z*Math.exp(-e.deltaY*.001)));s.style.transform=`translate(${x}px,${y}px) scale(${z})`};v.onpointerdown=e=>{start=[e.clientX-x,e.clientY-y];v.setPointerCapture(e.pointerId)};v.onpointermove=e=>{if(!start)return;x=e.clientX-start[0];y=e.clientY-start[1];const s=v.querySelector('svg');if(s)s.style.transform=`translate(${x}px,${y}px) scale(${z})`};v.onpointerup=()=>start=null});load();</script></html>'''
    (args.root/'shared-review.html').write_text(html,encoding='utf-8')
    # A figure from actual source/prediction files, with all five cases included.
    five=[r for r in present if r['cohort']=='five'];sheet=Image.new('RGB',(1536,560*len(five)),'white');d=ImageDraw.Draw(sheet)
    for i,r in enumerate(five):
        data=args.root/r['data'];pred=args.root/r['prediction']/'prediction.json'
        sheet.paste(Image.open(data/'input.png').convert('RGB'),(0,i*560+35));sheet.paste(render(json.loads((data/'target.json').read_text(encoding='utf-8'))),(512,i*560+35))
        if pred.exists():sheet.paste(render(json.loads(pred.read_text(encoding='utf-8'))),(1024,i*560+35))
        d.text((10,i*560+10),r['sample_id']+' | real input / CAD GT / MODEL '+args.stage,fill='black')
    sheet.save(args.root/(args.stage+'-five-review.jpg'))
    print(json.dumps({'review':str(args.root/'shared-review.html'),'figure':str(args.root/(args.stage+'-five-review.jpg'))}))
if __name__=='__main__':main()
