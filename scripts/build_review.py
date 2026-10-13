"""Build an offline private review gallery and evidence-backed pilot report."""
from __future__ import annotations
import argparse, collections, html, json
from pathlib import Path


def build(root: Path) -> dict:
    """Summarize real receipts and embed only redacted identifiers in the gallery."""
    rows=json.loads((root/'batch-results.json').read_text(encoding='utf-8'))
    for r in rows:
        folder=root/'samples'/r['sample_id']
        r['available_images']=[n for n in ['reference.jpg','cad-render.png','before-source-render.png','aligned-reference.jpg','alignment-overlay.png','matches.jpg','sheet-crop.png'] if (folder/n).exists()]
    successful=[r for r in rows if r['status']=='extracted_review_pending']
    integrity=json.loads((root/'cad-integrity-audit.json').read_text()) if (root/'cad-integrity-audit.json').exists() else []
    integrity_by_id={r['sample_id']:r for r in integrity}
    for r in rows:
        r['cad_integrity']=integrity_by_id.get(r['sample_id'])
    summary={'attempts':len(rows),'extracted':len(successful),'failed':len(rows)-len(successful),
             'dimension_status':dict(collections.Counter(r['dwg_dimensions']['status'] for r in successful)),
             'dimension_entities_checked':sum(r['dwg_dimensions']['expected_count'] for r in successful),
             'alignment_status':dict(collections.Counter(r['registration']['status'] for r in successful)),
             'unit_preservation_pass':sum(r['units_preserved'] for r in successful),
             'originals_unchanged_verified':sum(r.get('originals_unchanged') is True for r in rows),
             'human_approved':0,'split_assigned':False,'training_ready':False}
    summary['cad_integrity']={'audited':len(integrity),'duplicate_handle_samples':sum(r['dxf_duplicate_handle_groups']>0 for r in integrity),'audit_error_samples':sum(r['audit_errors']>0 for r in integrity),'audit_fix_samples':sum(r['audit_fixes']>0 for r in integrity)}
    summary['cad_integrity']['header_handseed_conflict_samples']=sum(r.get('cropped_dxf',{}).get('handseed_matches_existing_handle',False) for r in integrity)
    summary['cad_integrity']['loader_warning_samples']=sum(r.get('cropped_dxf',{}).get('load_duplicate_handle_warning_count',0)>0 for r in integrity)
    summary['cad_integrity']['dwg_reopened_duplicate_handle_samples']=sum(r.get('dwg_reopened_dxf',{}).get('duplicate_entity_handle_groups',0)>0 for r in integrity)
    maes=[r['roundtrip_render_mae'] for r in successful if r.get('roundtrip_render_mae') is not None]
    summary['same_viewport_render_comparison']={'measured':len(maes),'max_mae_0_255':max(maes) if maes else None}
    (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    public=[{'id':r['sample_id'],'status':r['status'],'images':r['available_images'],
             'dimensions':r.get('dwg_dimensions',{}),'registration':r.get('registration',{}),
             'units':r.get('source_units'),'units_preserved':r.get('units_preserved'),
             'crop':{k:v for k,v in r.get('crop',{}).items() if k!='anchors'},
             'error_type':r.get('error_type'),'originals_unchanged':r.get('originals_unchanged')} for r in rows]
    for item in public:item['cad_integrity']=integrity_by_id.get(item['id'])
    # This gallery remains in ignored outputs; no remote assets, customer paths or names.
    data=json.dumps(public,ensure_ascii=False).replace('</','<\\/')
    page=GALLERY.replace('__DATA__',data).replace('__SUMMARY__',html.escape(json.dumps(summary,ensure_ascii=False)))
    (root/'review.html').write_text(page,encoding='utf-8')
    lines=['# 준공도면–변경전 CAD 페어 pilot 검증 보고서','',
           '2026-10-13 KST · 실제 실행 결과 · 사내 검수 전용/외부 재배포 금지','',
           '## 결과','',f"- 시도 {summary['attempts']} / 추출 {summary['extracted']} / 실패 {summary['failed']}",
           f"- DWG 재열기 치수 대조: {summary['dimension_status']} / dimension 객체 {summary['dimension_entities_checked']}",
           f"- 이미지–CAD 자동 정합: {summary['alignment_status']}",
           f"- 원본 hash/size/mtime 보존 확인: {summary['originals_unchanged_verified']}/{summary['attempts']}",
           f"- 도면 unit header 보존: {summary['unit_preservation_pass']}/{summary['extracted']}",
           '- 사람 승인 0, split 미배정, 학습 준비 완료 아님.','',
           f"- CAD integrity: {summary['cad_integrity']}. 치수 보존 pass와 파일 무결성을 별도 판정한다. audit는 local DXF 메모리에서 검사했고 수정 결과를 저장하지 않았다.",
           f"- 동일 viewport 렌더 대조: {summary['same_viewport_render_comparison']}. backend 자동 figure 변경을 보정하고 실제 이미지 크기를 검증했다.",
           '## 선택과 방법','',
           '운영 워크 agent folder index를 인증된 읽기 전용 GET으로 수집했다. 중복 경로를 제거해 정렬한 뒤 seed 20261013으로 shuffle하고 immediate children만 검사했다. 정확한 준공도면 stem 및 변경전후.dwg 이름을 사용한다. 파일명 alias/다른 reference는 포함하지 않는다.',
           '60개 후보 중 앞 순서대로 시도하며 추출 성공 40개, 최대 시도 50개를 목표로 사전 고정했다. 전체 운영 자료의 성공률을 추정하는 무편향 벤치마크가 아니다. 실패도 분모에 포함한다.','',
           '원본 hash를 계산한 후 local copy만 ODA/ezdxf에서 열었다. 변경전/후 텍스트·도곽·inner frame detector를 읽기 전용으로 재사용했다. detector confidence는 calibrated 의미 확률이 아니며 사람 영역 검수가 필요하다.',
           '같은 crop viewport에서 원본 CAD와 DWG 재열기 렌더를 비교했다. DIMENSION의 수, 측정값, 기준점, 표시 override, dimlfac/dimscale/dimtxt/dimdec 등 스타일을 multiset으로 대조했다. 치수 없는 샘플은 pass가 아닌 not_applicable이다. 파일 format/단위 헤더 보존이 실제 실물 mm의 정확성을 뜻하지 않는다.',
           '정합은 grayscale/edge SIFT, ratio 0.72, RANSAC 4 resized pixels를 비교했다. candidate 조건: inlier>=20, ratio>=0.35, CAD inlier hull coverage>=0.15, convex mapped viewport 및 면적 비율 0.005~1.5. 선택된 homography와 matches를 저장했다. 정합 reprojection 잔차는 feature fitting 잔차이며 independent landmark나 치수 정확도 측정이 아니다.','',
           '## 검수 방법','',
           '[비교 화면](review.html)에서 입력·CAD·원본 CAD crop·정합/매칭 화면을 전환한다. 변경전 영역·동일 평면·정합과 실물 치수 신뢰도를 각각 판정한다. source/target 대응점은 두 이미지에서 같은 corner를 번갈아 클릭해 기록할 수 있다. 화면 판정/노트/대응점은 browser localStorage에 저장되며 JSON으로 내보내 결과를 보존한다. 내보내기 전 사람이 승인한 데이터는 manifest에 반영되지 않는다.',
           '정합 실패는 사진 왜곡, full-sheet/여러 평면, annotation·설계 차이, 반복 선/기호, 미승인 영역 문제를 구분해 검수한다. 일반 homography로 종이 휨을 해결했다고 주장하지 않는다. 사용자 대응점 기반 정합 또는 도면 ROI 선택은 다음 검수 단계다.','',
           '## 샘플별 결과','',
           '| 샘플 | 추출 | DWG 치수 | 정합 | 원본 무변경 |','| --- | --- | --- | --- | --- |']
    for r in rows:
        lines.append(f"| {r['sample_id']} | {r['status']} | {r.get('dwg_dimensions',{}).get('status','not-run')} | {r.get('registration',{}).get('status','not-run')} | {r.get('originals_unchanged','unknown')} |")
    lines+=['','## 증거·한계','',
            '`discovery.json`, `batch-results.json`, `summary.json`, sample별 `report.json`·원본 전후 hash·before.dxf/before.dwg·render·matches·worker log를 보존한다. 소스/산출물 SHA-256과 detector hash가 sample receipt에 있다. 원본/내부 경로가 들어간 manifest와 실제 도면은 Git에 올리지 않는다.',
            'DWG roundtrip 검증은 ODA 엔진 재열기 기준이다. 실제 업무 CAD UI에서 수정·저장한 사용자 roundtrip은 미실행이다. before semantics·dimension display·정합은 비교 화면으로 추가 검수한다. 완료 DWG는 wall semantic label 또는 사람의 drawing action 기록을 자동 제공하지 않는다.','']
    (root/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    return summary


GALLERY='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>img2dwg 사내 페어 검수</title>
<style>body{margin:0;font:15px system-ui;background:#101820;color:#e8eef3}header{padding:18px;background:#18252f;position:sticky;top:0;z-index:2}button,select,input,textarea{font:inherit;padding:9px;border-radius:7px;margin:3px;border:1px solid #516572}button{cursor:pointer}main{padding:18px}.panels{display:grid;grid-template-columns:1fr 1fr;gap:12px}.panel{background:#263541;padding:12px;border-radius:10px}.viewport{height:65vh;overflow:auto;background:#eee;position:relative}img{width:100%;height:auto;display:block;cursor:crosshair}textarea{width:95%;min-height:65px}pre{white-space:pre-wrap;font-size:13px}h2{font-size:18px}.warning{color:#ffd486}a{color:#70d7ed}small{color:#aec1cf}.dot{position:absolute;background:#f22;color:white;border-radius:50%;width:20px;height:20px;text-align:center;pointer-events:none}</style>
<header><b>준공도면–변경전 CAD 검수</b><select id="sample"></select><button onclick="step(-1)">이전</button><button onclick="step(1)">다음</button><button onclick="exportReviews()">검수 JSON 내보내기</button><a href="report.md">실행 보고서</a><p class="warning">사내 전용 · 원본 무변경 · 자동 정합은 후보이며 사람 승인이 아닙니다.</p></header>
<main><details><summary>전체 실행 요약</summary><pre>__SUMMARY__</pre></details><h2 id="title"></h2>
<div class="panels"><div class="panel"><b>준공도면 (원본 EXIF 방향 반영 preview)</b><div id="leftview" class="viewport"><img id="input"></div></div><div class="panel"><select id="mode"></select><button onclick="zoom(1.3)">확대</button><button onclick="zoom(1/1.3)">축소</button><div id="rightview" class="viewport"><img id="cad"></div></div></div>
<p><small>확대는 두 이미지에 적용됩니다. 대응점 기록: 입력 이미지→CAD 렌더의 같은 corner를 번갈아 클릭하세요. 점을 기록할 때 우측 모드는 CAD 렌더로 고정합니다. 빨강 점 숫자와 실제 이미지 픽셀 좌표를 내보냅니다.</small><button onclick="clearPoints()">대응점 초기화</button><span id="pointstatus"></span></p>
<div class="panels"><div class="panel"><h2>사람 판정 (로컬 저장)</h2><label>변경전 영역 <select id="before"><option value="pending">미검수</option><option value="correct">영역 맞음</option><option value="wrong">영역 틀림</option><option value="recrop">재추출 필요</option></select></label><br><label>이미지–CAD <select id="alignment"><option value="pending">미검수</option><option value="same-plan-needs-alignment">같은 평면·정합 보정 필요</option><option value="aligned">정합 확인</option><option value="mismatch">다른 평면/상태</option></select></label><br><label>치수 <select id="dimension"><option value="pending">미검수</option><option value="display-preserved">표시/값 보존 확인</option><option value="metric-anchor-approved">실물 단위/anchor 확인</option><option value="needs-review">치수 추가 확인</option></select></label><br><textarea id="notes" placeholder="영역·변경상태·사진 왜곡·치수 문제와 수정 메모"></textarea><button onclick="save()">현재 판정 저장</button><p id="saveinfo"></p></div><div class="panel"><h2>자동 검사 근거</h2><pre id="metrics"></pre><p id="downloads"></p></div></div></main>
<script>const samples=__DATA__;const key='img2dwg-pilot-20261013-v1';let reviews=JSON.parse(localStorage.getItem(key)||'{}');let idx=0,z=1;const $=id=>document.getElementById(id);const labels={'cad-render.png':'DWG 재열기 CAD 렌더','before-source-render.png':'원본 CAD 변경전 crop','aligned-reference.jpg':'자동 정합된 준공도면','alignment-overlay.png':'정합 선 오버레이','matches.jpg':'자동 특징점 대응','sheet-crop.png':'전체 DWG + 추출 영역'};samples.forEach((s,i)=>$('sample').add(new Option(s.id+' · '+s.status,i)));$('sample').onchange=()=>{save(false);idx=+$('sample').value;show()};$('mode').onchange=()=>{imageMode();dots()};
function current(){return samples[idx]}function path(n){return 'samples/'+current().id+'/'+n}function show(){let s=current();z=1;$('sample').value=idx;$('title').textContent=s.id+' · '+s.status;$('input').src=path('reference.jpg');$('mode').innerHTML='';s.images.filter(n=>n!=='reference.jpg').forEach(n=>$('mode').add(new Option(labels[n]||n,n)));if(s.images.includes('cad-render.png'))$('mode').value='cad-render.png';imageMode();let r=reviews[s.id]||{};['before','alignment','dimension'].forEach(k=>$(k).value=r[k]||'pending');$('notes').value=r.notes||'';$('metrics').textContent=JSON.stringify({crop:s.crop,dimension_status:s.dimensions.status,expected_dimensions:s.dimensions.expected_count,missing_changed:s.dimensions.missing_or_changed,added_changed:s.dimensions.added_or_changed,unit_header:s.units,units_preserved:s.units_preserved,registration:s.registration,cad_integrity:s.cad_integrity,originals_unchanged:s.originals_unchanged,error_type:s.error_type},null,2);$('downloads').innerHTML='<a href="'+path('report.json')+'">상세 receipt</a> · <a href="'+path('before.dwg')+'">변경전 DWG</a> · <a href="'+path('before.dxf')+'">DXF</a>';$('saveinfo').textContent='';$('input').onload=dots;$('cad').onload=dots;dots()}
function imageMode(){$('cad').src=path($('mode').value);$('input').style.width=(100*z)+'%';$('cad').style.width=(100*z)+'%'}function zoom(f){z=Math.max(.5,Math.min(5,z*f));imageMode();dots()}
function save(message=true){let r=reviews[current().id]||{};['before','alignment','dimension'].forEach(k=>r[k]=$(k).value);r.notes=$('notes').value;r.updated_at=new Date().toISOString();reviews[current().id]=r;localStorage.setItem(key,JSON.stringify(reviews));if(message)$('saveinfo').textContent='저장됨. JSON 내보내기로 파일에 보존하세요.'}function step(d){save(false);idx=Math.max(0,Math.min(samples.length-1,idx+d));show()}
function mark(which,e){if($('mode').value!=='cad-render.png'){$('pointstatus').textContent='대응점 기록은 CAD 렌더 모드에서 하세요.';return}let r=reviews[current().id]||{};r.points=r.points||[];let expected=r.points.length%2===0?'input':'cad';if(which!==expected){$('pointstatus').textContent=expected==='input'?'입력 이미지 점을 먼저 클릭하세요.':'CAD의 같은 점을 클릭하세요.';return}let im=$(which),b=im.getBoundingClientRect();r.points.push({surface:which,x:(e.clientX-b.left)/b.width*im.naturalWidth,y:(e.clientY-b.top)/b.height*im.naturalHeight,width:im.naturalWidth,height:im.naturalHeight});reviews[current().id]=r;save(false);dots()}
$('input').onclick=e=>mark('input',e);$('cad').onclick=e=>mark('cad',e);function dots(){document.querySelectorAll('.dot').forEach(d=>d.remove());let p=(reviews[current().id]||{}).points||[];p.forEach((t,i)=>{let im=$(t.surface);if(t.surface==='cad'&&$('mode').value!=='cad-render.png')return;let v=t.surface==='input'?$('leftview'):$('rightview');let d=document.createElement('span');d.className='dot';d.textContent=Math.floor(i/2)+1;d.style.left=(t.x/t.width*im.clientWidth-10)+'px';d.style.top=(t.y/t.height*im.clientHeight-10)+'px';v.appendChild(d)});$('pointstatus').textContent=Math.floor(p.length/2)+' 쌍 기록'}function clearPoints(){let r=reviews[current().id]||{};r.points=[];reviews[current().id]=r;save(false);dots()}function exportReviews(){save(false);let blob=new Blob([JSON.stringify({schema:'img2dwg-human-review/v1',pilot:'2026-10-13',exported_at:new Date().toISOString(),reviews},null,2)],{type:'application/json'});let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='pilot-human-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}show();</script></html>'''


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);build(p.parse_args().root)
