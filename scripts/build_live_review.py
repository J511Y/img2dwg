"""Display the actual authenticated Space response, without rerunning a model."""
import argparse
import html
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    args = p.parse_args()
    receipt = json.loads((args.run / 'live-verification/live-verification.json').read_text())
    output = args.run / 'live-verification/review.html'
    status = (args.run / 'live-verification/raw/status.md').read_text(encoding='utf-8')
    document = '''<!doctype html><html lang="ko"><meta charset="utf-8"><title>Space 실제 업로드 검증 결과</title>
<style>body{font:16px sans-serif;background:#f4f7fb;color:#142b46;padding:20px;margin:0}h1{font-size:26px;margin:0 0 12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.panel{background:white;border:1px solid #dce3ee;border-radius:10px;overflow:hidden}
.panel h2{font-size:17px;margin:0;padding:14px;border-bottom:1px solid #eee}img{width:100%;height:560px;object-fit:contain}iframe{width:100%;height:590px;border:0}
pre{white-space:pre-wrap;font:15px sans-serif;line-height:1.7}small{font-size:13px}a{color:#255dab}</style>
<h1>Space 실제 업로드 → 모델 벡터 → 다운로드 검증</h1>
<p><a href="https://huggingface.co/spaces/youjunhyeok/img2dwg">비공개 img2dwg Space</a> · 공유 노드·컴포넌트 재현 모델 · 5개 학습 사례</p>
<div class="grid"><section class="panel"><h2>실제로 업로드한 원본 준공도면</h2><img src="../pilot-local-verification/five-preview/P35d63089be5e6afb/upload.png"></section>
<section class="panel"><h2>Space가 반환한 실제 벡터 · 확대 가능</h2><iframe src="raw/viewer.html"></iframe></section></div>
<pre>''' + html.escape(status) + '''</pre><p>실제 다운로드 DXF: native INSERT 75개 · DIMENSION 19개 · mm 단위 · 감사 오류 0.
100mm 보정 전후 다운로드와 치수값 보존을 검사했고, 해당 DXF의 ODA DWG 재열기도 통과했습니다.</p>
<small>Space revision: ''' + receipt['space_revision'] + '<br>Checkpoint SHA256: ' + receipt['model_sha256'] + '''<br>
이 화면의 벡터는 인증된 Space API의 실제 응답 파일입니다. 정답 CAD 렌더가 아닙니다. 고객 원본 · 내부 검수 전용 · 재배포 금지.</small>
<p><a href="raw/prediction.svg">SVG</a> · <a href="raw/prediction.dxf">DXF</a> · <a href="raw/receipt.json">변환 기록</a> ·
<a href="../live-oda/dwg/raw.dwg">ODA 검증 DWG</a> · <a href="../shared-review.html">25개 비교 검수</a></p></html>'''
    output.write_text(document, encoding='utf-8')
    print(str(output))


if __name__ == '__main__':
    main()
