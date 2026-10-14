"""Private, interactive original/GT/predicted-vector and dimension comparison."""
import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from img2dwg.raw_evaluation import measurement

PAGE = r'''<!doctype html><html lang="ko"><meta charset="utf-8">
<title>img2dwg 실제 페어 검증</title>
<style>
*{box-sizing:border-box}body{margin:0;font:15px system-ui;background:#f3f5f8;color:#162535}
header{padding:22px 28px;background:#fff;border-bottom:1px solid #dde3eb}h1{margin:0 0 12px;font-size:24px}
.status{padding:12px;background:#fff0ef;border:1px solid #f1b2ac;border-radius:8px;line-height:1.6}
.counts{display:flex;gap:16px;flex-wrap:wrap;margin-top:14px}.counts span{background:#edf1f6;padding:8px 14px;border-radius:6px}
main{padding:18px 28px}select,button{font:inherit;padding:8px 12px;border:1px solid #cad3df;border-radius:6px;background:white}
nav{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px}.cols{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
section{background:white;border:1px solid #dde3eb;border-radius:9px;overflow:hidden}h2{font-size:16px;margin:0;padding:12px 15px;min-height:62px;border-bottom:1px solid #eee}
.view{height:560px;background:white;position:relative;overflow:hidden;touch-action:none}.view svg{width:100%;height:100%;cursor:grab}.view img{width:100%;height:100%;object-fit:contain}
.hint{padding:8px 12px;font-size:12px;color:#66798b;background:#fafbfc}.metrics{padding:14px;margin:14px 0;line-height:1.8}
table{width:100%;border-collapse:collapse;background:white;margin-top:10px}th,td{padding:8px 12px;border-bottom:1px solid #e4e9f0;text-align:right}th:first-child,td:first-child{text-align:left}
.fail{color:#ae2c25}.good{color:#167355}.badge{font-size:12px;color:#fff;background:#ae2c25;padding:3px 7px;border-radius:4px}.downloads a{margin-right:16px}
@media(max-width:1100px){main{padding:14px}.view{height:390px}h2{font-size:14px}}
@media(max-width:700px){.cols{grid-template-columns:1fr}.view{height:480px}}
</style><header><h1>실제 준공도면 → CAD 복원 검증</h1><div class="status" id="headline"></div><div class="counts" id="counts"></div></header>
<main><nav><button id="previous">← 이전</button><select id="choose"></select><button id="next">다음 →</button><button id="reset">벡터 전체 보기</button><label><input id="overlay" type="checkbox"> 예측 위에 정답 겹치기</label></nav>
<div class="cols"><section><h2>① 실제 입력 · 원본 준공도면</h2><div class="view" id="input"></div><div class="hint">EXIF 방향 적용·종횡비 유지. CAD 합성 입력 아님.</div></section>
<section><h2>② 정답 · 같은 의뢰의 변경전 CAD</h2><div class="view" id="target"></div><div class="hint">휠 확대·드래그 이동 · 정답 컴포넌트/치수</div></section>
<section><h2>③ 모델 예측 · 실제 벡터</h2><div class="view" id="prediction"></div><div class="hint">휠 확대·드래그 이동 · 정답 조회/래스터 삽입 없음</div></section></div>
<section class="metrics"><div id="metrics"></div><div class="downloads" id="downloads"></div></section>
<section><h2>치수 숫자와 실제 벡터 길이 검사 (mm)</h2><div id="dimensions"></div></section>
<p>위치는 고정된 canonical CAD 좌표계로 평가했습니다. 정답에 맞춘 축척·정합 보정은 하지 않았습니다. 두 CAD 창의 겹치기는 원본 이미지와의 특징점 대응을 의미하지 않습니다.</p>
<p>구조 매칭 허용 오차 10mm, 치수값·측정 길이 오차 1mm 이하, 필요한 치수 누락 0개가 수치 기준입니다. 학습 5개 재현은 일반화 성능이 아닙니다. 기본 서비스 재배포 여부는 20개 검증과 CAD 검사를 함께 따릅니다.</p>
</main><script>
const data=__DATA__;let current=0;const q=s=>document.querySelector(s);const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>n===null||n===undefined?'미측정':Number(n).toFixed(2);let targets={};
q('#headline').textContent=data.headline;q('#counts').innerHTML=data.totals.map(x=>`<span>${esc(x)}</span>`).join('');
q('#choose').innerHTML=data.rows.map((r,i)=>`<option value="${i}">${r.split==='train'?'학습 재현':'별도 검증'} ${r.position} · ${r.id} · ${r.passed?'수치 기준 통과':'미통과'}</option>`).join('');
function panzoom(svg){let box=[0,0,512,512];svg.setAttribute('viewBox',box.join(' '));let drag=null;
svg.addEventListener('wheel',e=>{e.preventDefault();let rect=svg.getBoundingClientRect(),f=e.deltaY<0?.85:1.18;
let x=(e.clientX-rect.left)/rect.width,y=(e.clientY-rect.top)/rect.height;box=[box[0]+box[2]*x*(1-f),box[1]+box[3]*y*(1-f),box[2]*f,box[3]*f];svg.setAttribute('viewBox',box.join(' '));},{passive:false});
svg.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY,...box];svg.setPointerCapture(e.pointerId)});
svg.addEventListener('pointermove',e=>{if(!drag)return;let r=svg.getBoundingClientRect();box=[drag[2]-(e.clientX-drag[0])/r.width*drag[4],drag[3]-(e.clientY-drag[1])/r.height*drag[5],drag[4],drag[5]];svg.setAttribute('viewBox',box.join(' '));});
svg.addEventListener('pointerup',()=>drag=null);svg.addEventListener('pointercancel',()=>drag=null);return ()=>{box=[0,0,512,512];svg.setAttribute('viewBox',box.join(' '));};}
async function vector(id,path){const host=q(id);host.innerHTML='불러오는 중';try{let text=await(await fetch(path)).text();let doc=new DOMParser().parseFromString(text,'image/svg+xml');let svg=doc.documentElement;if(svg.tagName.toLowerCase()!=='svg')throw Error('SVG absent');svg.setAttribute('aria-label',id==='#target'?'정답 CAD 벡터':'모델 예측 벡터');host.replaceChildren(document.importNode(svg,true));targets[id]=panzoom(host.firstElementChild);}catch(e){host.textContent='출력 없음 / '+e.message;}}
async function show(){const r=data.rows[current];q('#choose').value=current;q('#metrics').textContent='선택한 사례를 불러오는 중';q('#dimensions').innerHTML='';q('#downloads').innerHTML='';q('#input').innerHTML=`<img src="${esc(r.input)}" alt="실제 입력 도면">`;
await Promise.all([vector('#target',r.target),vector('#prediction',r.prediction)]);
if(q('#overlay').checked){let svg=q('#prediction svg'),gt=q('#target svg');if(svg&&gt){let g=document.createElementNS('http://www.w3.org/2000/svg','g');g.setAttribute('opacity','.35');g.innerHTML=gt.innerHTML;g.querySelectorAll('rect[fill="white"]').forEach(x=>x.remove());g.querySelectorAll('[stroke]').forEach(x=>x.setAttribute('stroke','#db362f'));svg.appendChild(g);}}
q('#metrics').innerHTML=`<b>${r.passed?'수치 기준 통과':'검증 미통과'}</b> · 구조 F1 ${fmt(r.structure_f1*100)}%<br>필요 치수 ${r.required_dimensions}개 · 위치·수치·길이가 모두 맞는 치수 ${r.correct_dimensions}개 · 누락/오류 ${r.missing_dimensions}개<br>DXF 검사 ${r.audit_errors===0?'파일 재열기 통과':'실패/미완료'} · <b>파일 검사 결과는 구조·치수 복원 성공과 구분합니다.</b>`;
q('#downloads').innerHTML=`<a href="${esc(r.prediction)}" download>예측 SVG</a><a href="${esc(r.dxf)}" download>예측 DXF</a><a href="${esc(r.json)}" download>좌표 JSON</a><a href="${esc(r.metrics)}" download>검증 기록</a>`;
q('#dimensions').innerHTML=`<table><thead><tr><th>정답 치수</th><th>정답 값</th><th>예측 숫자</th><th>실제 벡터 측정</th><th>숫자 오차</th><th>길이 오차</th><th>위치 오차</th></tr></thead><tbody>${r.dimensions.map(d=>`<tr class="${d.correct?'good':'fail'}"><td>${esc(d.label)}</td><td>${fmt(d.target)}</td><td>${fmt(d.predicted)}</td><td>${fmt(d.vector_measurement)}</td><td>${fmt(d.numeric_error)}</td><td>${fmt(d.geometry_error)}</td><td>${fmt(d.position_error)}</td></tr>`).join('')}</tbody></table>`;}
q('#choose').onchange=e=>{current=Number(e.target.value);show()};q('#previous').onclick=()=>{current=(current+data.rows.length-1)%data.rows.length;show()};q('#next').onclick=()=>{current=(current+1)%data.rows.length;show()};q('#reset').onclick=()=>Object.values(targets).forEach(f=>f());q('#overlay').onchange=show;show();
</script></html>'''


def build(root, run):
    evaluation = json.loads((run / 'evaluation.json').read_text())
    items = json.loads((root / 'data/index.json').read_text())
    rows = []
    for index, item in enumerate(items):
        key = item['sample_id']; split = item['split']; prefix = 'train-preview' if split == 'train' else 'validation-preview'
        folder = run / prefix / key
        target = json.loads((root / 'data' / key / 'target.json').read_text())
        prediction = json.loads((folder / 'prediction.json').read_text())
        metrics = json.loads((folder / 'metrics.json').read_text())
        p_dims = [c for c in prediction['components'] if c['kind'] == 'dimension']
        t_dims = [c for c in target['components'] if c['kind'] == 'dimension']
        matched = {d['target_index']: d for d in metrics['dimension_details']}
        dimensions = []
        for i, c in enumerate(t_dims):
            record = matched.get(i); pred = p_dims[record['predicted_index']] if record else None
            dimensions.append({'label': f'D{i + 1}', 'target': c['measurement_mm'],
                'predicted': pred.get('predicted_value_mm') if pred else None,
                'vector_measurement': measurement(pred, prediction) if pred else None,
                'numeric_error': record['numeric_error_mm'] if record else None,
                'geometry_error': record['geometry_error_mm'] if record else None,
                'position_error': record['max_point_error_mm'] if record else None,
                'correct': bool(record and record['numeric_error_mm'] <= 1 and record['geometry_error_mm'] <= 1
                                and record['label_geometry_residual_mm'] <= 1 and record['max_point_error_mm'] <= 10)})
        paths = {name: (folder / file).relative_to(root).as_posix() for name, file in
                 [('prediction', 'prediction.svg'), ('dxf', 'prediction.dxf'), ('json', 'prediction.json'), ('metrics', 'metrics.json')]}
        rows.append({'id': key, 'split': split, 'position': index + 1 if split == 'train' else index - 4,
                     'input': f'data/{key}/input.png', 'target': f'data/{key}/factory/prediction.svg',
                     **paths, 'passed': metrics['passed'], 'structure_f1': metrics['structure_f1'],
                     'required_dimensions': len(t_dims),
                     'correct_dimensions': metrics['components']['dimension']['correct_geometry_and_value'],
                     'missing_dimensions': metrics['components']['dimension']['missing_or_incorrect'],
                     'audit_errors': metrics['factory']['audit_errors'] if metrics['factory'] else None,
                     'dimensions': dimensions})
    passed = evaluation['train']['aggregate']['passed_cases'] == 5 and evaluation['validation']['aggregate']['passed_cases'] == 20
    data = {'headline': '수치 검증 결과 확인 필요' if passed else '모델이 구조·필수 치수 기준을 통과하지 못했습니다. Space 모델 재배포를 진행하지 않았습니다.',
            'totals': [f'실제 학습 5개: 통과 {evaluation["train"]["aggregate"]["passed_cases"]}/5',
                       f'별도 실제 검증 20개: 통과 {evaluation["validation"]["aggregate"]["passed_cases"]}/20',
                       '필요 치수 588개', '출력 SVG·DXF 벡터'], 'rows': rows}
    page = PAGE.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    # The UI text is Korean; identifiers and source drawings remain private.
    page = page.replace('読込中', '불러오는 중').replace('出力なし', '출력 없음').replace('実際の入力図面', '실제 입력 도면')
    (root / 'review.html').write_text(page, encoding='utf-8')
    (root / 'review-data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'cases': len(rows), 'page': str((root / 'review.html').resolve()), 'model_numeric_passed': passed}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True); p.add_argument('--run', type=Path, required=True)
    a = p.parse_args(); build(a.root, a.run)
