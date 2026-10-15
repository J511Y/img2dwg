"""Private three-column review of all frozen-candidate retention10/twenty20."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw
from img2dwg.vector import svg
from img2dwg.cad import render

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root;fresh=root/'CPU-fresh';r=json.loads((fresh/'receipt.json').read_text());training=json.loads((root/'GPU/receipt.json').read_text())
    assert r['model_sha256']==training['model_sha256']
    rows=json.loads((fresh/'index.json').read_text());assert len(rows)==30
    state={'schema':'full-continuation-review/v1','model_sha256':r['model_sha256'],'training':{k:training[k] for k in ['stopping_reason','updates','unique_training_exposed','complete_first_pass','quality_status','elapsed_seconds']},
           'retention':r['retention']['aggregate'],'twenty':r['twenty']['aggregate'],
           'baseline_twenty':r.get('baseline_twenty',{}).get('aggregate'),'Space_deployed':False,'rows':[]}
    for x in rows:
        k=x['sample_id'];group='retention' if x['split']=='train' else 'twenty';d=fresh/'review-data'/k;pred=fresh/(group+'-final')/k
        g=json.loads((d/'target.json').read_text(encoding='utf-8'));(d/'target.svg').write_text(svg(g),encoding='utf-8')
        m=json.loads((pred/'metrics.json').read_text());assert (pred/'prediction.svg').exists() and (pred/'prediction.dxf').exists()
        state['rows'].append({**x,'data':d.relative_to(root).as_posix(),'prediction':pred.relative_to(root).as_posix(),
            'passed':m['passed'],'structure_f1':m['structure_f1'],'component_f1':m['component_f1'],'reference_f1':m['shared_reference_f1'],
            'correct_dimensions':m['components']['dimension']['correct_geometry_and_value'],'required_dimensions':m['components']['dimension']['target'],
            'prediction_DXF_sha256':hashlib.sha256((pred/'prediction.dxf').read_bytes()).hexdigest()})
    (root/'full-continuation-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    html=r'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>EXP-054 본학습 · 실제 결과 검수</title>
<style>body{font:15px system-ui;margin:20px;background:#f5f7fb;color:#17304c}h1{font-size:25px}table{border-collapse:collapse;width:100%;background:white;margin:15px 0}th,td{border:1px solid #d5dce8;padding:7px;text-align:left}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.panel{background:white;padding:12px;border:1px solid #d5deeb;border-radius:8px}.view{height:550px;overflow:hidden;cursor:grab}.view img,.view svg{width:100%;height:100%;object-fit:contain;transform-origin:center}button,select{font:inherit;padding:7px}.metrics{white-space:pre-wrap;background:white;padding:14px;margin:15px 0}.bad{color:#a32832}.good{color:#13734c}a{color:#164dc1}</style>
<h1>EXP-054 · 1,028개 본학습 / 기존10 유지 / 별도20 검수</h1><div id="summary" class="metrics"></div>
<p>기존10은 동결한 검증 모델과 보호 분기로 유지한 train 사례입니다. 새 현장 성능은 별도20에서 확인합니다. 전부 실제 이미지→모델 예측이며, 정답 CAD는 가운데 열에만 표시합니다. 휠 확대 · 드래그 이동.</p>
<select id="cases"></select> <button id="prev">이전</button> <button id="next">다음</button> <button id="reset">뷰 초기화</button>
<div class="grid"><section class="panel"><b>① 입력 · 실제 준공도면</b><div class="view" id="input"></div></section><section class="panel"><b>② 정답 · 같은 의뢰 변경전 CAD</b><div class="view" id="truth"></div></section><section class="panel"><b>③ 동결 후보 · 실제 모델 벡터</b><div class="view" id="prediction"></div></section></div>
<div id="metrics" class="metrics"></div><p id="downloads"></p><table><thead><tr><th>정답 mm</th><th>예측 숫자 mm</th><th>참조점 오차 mm</th><th>숫자 오차 mm</th><th>실제 길이 오차 mm</th></tr></thead><tbody id="dims"></tbody></table>
<details open><summary>전체30개 결과 · 실패 포함</summary><table><thead><tr><th>사례</th><th>구분</th><th>구조F1</th><th>컴포넌트F1</th><th>공유관계F1</th><th>필수치수</th><th>수치판정</th></tr></thead><tbody id="all"></tbody></table></details>
<script>let state,index=10;const $=x=>document.getElementById(x);const fmt=x=>x==null?'미측정':Number(x).toFixed(3);let views=[];
async function show(){const r=state.rows[index];$('cases').value=index;views.forEach(v=>v.reset());$('input').innerHTML='<img src="'+r.data+'/input.png">';$('truth').innerHTML=await(await fetch(r.data+'/target.svg')).text();$('prediction').innerHTML=await(await fetch(r.prediction+'/prediction.svg')).text();const m=await(await fetch(r.prediction+'/metrics.json')).json();const raw=m.before_constraints||{},q=m.query_selection_receipt||{},c=m.constraint_receipt||{};$('metrics').className='metrics '+(m.passed?'good':'bad');$('metrics').textContent=(m.passed?'수치 검사 통과 · 직접 검수/모델 전체 gate 별도':'미통과 · 배포 금지')+'\n구조 '+fmt(m.structure_f1)+' / 컴포넌트 '+fmt(m.component_f1)+' / 공유관계 '+fmt(m.shared_reference_f1)+'\n필수 치수 '+r.correct_dimensions+'/'+r.required_dimensions+' · 추가 치수 '+m.components.dimension.extra_predicted+'\n제약 전 구조 '+fmt(raw.structure_f1)+' · 거부 DIM 후보 '+(q.rejected_dimension_candidates||[]).length+' · 제약 상태 '+(c.status||'applied')+' · 최대 보정 '+fmt(c.maximum_node_displacement_mm)+' mm\n'+(m.export_error||'');$('dims').innerHTML=m.dimension_details.map(d=>'<tr>'+[d.target_value_mm,d.predicted_value_mm,d.max_point_error_mm,d.numeric_error_mm,d.geometry_error_mm].map(v=>'<td>'+fmt(v)+'</td>').join('')+'</tr>').join('');$('downloads').innerHTML='<a href="'+r.prediction+'/prediction.dxf" download>실제 모델 DXF</a> · <a href="'+r.prediction+'/shared-graph.json">공유 그래프</a> · <a href="'+r.prediction+'/raw.svg">제약 적용 전 벡터</a>';}
async function load(){state=await(await fetch('full-continuation-state.json')).json();const t=state.training,a=state.retention,b=state.twenty;$('summary').textContent='본학습 노출 '+t.unique_training_exposed+'/1028 · '+t.updates+' updates · 종료 '+t.stopping_reason+'\n기존10 '+a.passed_cases+'/10 · 필수치수 '+a.dimensions_correct_geometry_and_value+'/'+a.required_dimensions+'\n별도20 '+b.passed_cases+'/20 · 필수치수 '+b.dimensions_correct_geometry_and_value+'/'+b.required_dimensions+'\nEXP053 기준선20 '+(state.baseline_twenty?state.baseline_twenty.passed_cases+'/20':'미측정')+'\nSpace '+(state.Space_deployed?'반영 완료':'미반영 · 전체 검수 gate 확인 필요')+'\ncheckpoint SHA256 '+state.model_sha256;state.rows.forEach((r,i)=>{$('cases').add(new Option((r.split==='train'?'기존10':'별도20')+' · '+r.sample_id+' · '+r.correct_dimensions+'/'+r.required_dimensions,i));const tr=document.createElement('tr');tr.className=r.passed?'good':'bad';tr.innerHTML='<td><button data-i="'+i+'">'+r.sample_id+'</button></td><td>'+(r.split==='train'?'기존 train':'별도 검증')+'</td><td>'+fmt(r.structure_f1)+'</td><td>'+fmt(r.component_f1)+'</td><td>'+fmt(r.reference_f1)+'</td><td>'+r.correct_dimensions+'/'+r.required_dimensions+'</td><td>'+(r.passed?'pass':'fail')+'</td>';$('all').append(tr)});$('all').onclick=e=>{if(e.target.dataset.i){index=Number(e.target.dataset.i);show();window.scrollTo(0,0)}};await show()}
$('cases').onchange=()=>{index=Number($('cases').value);show()};$('prev').onclick=()=>{index=(index+29)%30;show()};$('next').onclick=()=>{index=(index+1)%30;show()};$('reset').onclick=()=>views.forEach(v=>v.reset());document.querySelectorAll('.view').forEach(v=>{let z=1,x=0,y=0,start=null;const apply=()=>{const s=v.querySelector('svg');if(s)s.style.transform=`translate(${x}px,${y}px) scale(${z})`};views.push({reset:()=>{z=1;x=0;y=0;apply()}});v.onwheel=e=>{if(!v.querySelector('svg'))return;e.preventDefault();z=Math.min(30,Math.max(.1,z*Math.exp(-e.deltaY*.001)));apply()};v.onpointerdown=e=>{start=[e.clientX-x,e.clientY-y];v.setPointerCapture(e.pointerId)};v.onpointermove=e=>{if(!start)return;x=e.clientX-start[0];y=e.clientY-start[1];apply()};v.onpointerup=()=>start=null});load();</script></html>'''
    (root/'full-continuation-review.html').write_text(html,encoding='utf-8')
    groups=[('original',[r for r in state['rows'] if r['cohort']=='original']),('additional',[r for r in state['rows'] if r['cohort']=='additional'])]
    twenty=[r for r in state['rows'] if r['split']=='validation']
    groups += [('twenty-'+str(i+1),twenty[i*4:(i+1)*4]) for i in range(5)]
    for name,selected in groups:
        contact=Image.new('RGB',(1536,550*len(selected)),'white');draw=ImageDraw.Draw(contact)
        sources=[]
        for i,r in enumerate(selected):
            d=root/r['data'];pred=root/r['prediction'];contact.paste(Image.open(d/'input.png').convert('RGB'),(0,i*550+30))
            contact.paste(render(json.loads((d/'target.json').read_text(encoding='utf-8'))),(512,i*550+30));contact.paste(render(json.loads((pred/'prediction.json').read_text(encoding='utf-8'))),(1024,i*550+30))
            draw.text((10,i*550+8),r['sample_id']+' | INPUT / GT / MODEL | DIM '+str(r['correct_dimensions'])+'/'+str(r['required_dimensions'])+' | F1 '+str(round(r['structure_f1'],5)),fill='black')
            sources.append({'sample_id':r['sample_id'],'input_sha256':hashlib.sha256((d/'input.png').read_bytes()).hexdigest(),
                'GT_sha256':hashlib.sha256((d/'target.json').read_bytes()).hexdigest(),
                'prediction_sha256':hashlib.sha256((pred/'prediction.json').read_bytes()).hexdigest()})
        image=root/('full-'+name+'.jpg');contact.save(image)
        image.with_suffix('.provenance.json').write_text(json.dumps({'derived_from_actual_run':True,'sources':sources,
            'model_sha256':state['model_sha256'],'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
            'image_size':contact.size,'image_bytes':image.stat().st_size,
            'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'transformation':'PIL native vector rendering;three512px columns;no geometry fitting or editing',
            'redistribution':'prohibited;controlled internal/private only'},indent=2),encoding='utf-8')
    print(json.dumps({'review':str(root/'full-continuation-review.html'),'cases':30,'contact_sheets':7}))
if __name__=='__main__':main()
