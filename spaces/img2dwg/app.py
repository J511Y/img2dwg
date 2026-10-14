"""Private image-to-shared-component pilot; all vectors are model predictions."""
import collections
import html
import json
import os
import tempfile
import threading
from pathlib import Path

import gradio as gr
import torch
from huggingface_hub import snapshot_download
from img2dwg.shared_inference import load as load_model, predict
from img2dwg.structured import compile_graph
from img2dwg.vector import exports, svg

torch.set_num_threads(int(os.getenv('TORCH_THREADS', '2')))
LOADED = None
LOCK = threading.Lock()


def load():
    global LOADED
    if LOADED is None:
        with LOCK:
            if LOADED is None:
                directory = os.getenv('LOCAL_MODEL_DIR') or snapshot_download(
                    os.environ['MODEL_REPO'], revision=os.environ['MODEL_REVISION'],
                    allow_patterns=['model.safetensors', 'config.json', 'library.json', 'release.json'])
                LOADED = load_model(directory, os.environ['MODEL_SHA256'])
    return LOADED


def viewer(graph):
    document = '''<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;background:#f1f5f9;font:14px sans-serif}nav{padding:8px;display:flex;gap:8px;align-items:center}
    button{border:1px solid #ccd2db;border-radius:5px;background:white;padding:5px 12px;cursor:pointer}
    #view{height:520px;background:white;cursor:grab;overflow:hidden}svg{display:block;width:100%;height:100%}
    </style></head><body><nav><button id="plus">＋</button><button id="minus">－</button><button id="reset">전체</button>
    <span>휠로 확대 · 드래그로 이동</span></nav><div id="view">''' + svg(graph) + '''</div><script>
    const s=document.querySelector('svg'),original=s.getAttribute('viewBox').split(' ').map(Number);let v=[...original],drag=null;
    function draw(){s.setAttribute('viewBox',v.join(' '))}function zoom(f,x=.5,y=.5){v=[v[0]+v[2]*x*(1-f),v[1]+v[3]*y*(1-f),v[2]*f,v[3]*f];draw()}
    document.querySelector('#plus').onclick=()=>zoom(.8);document.querySelector('#minus').onclick=()=>zoom(1.25);
    document.querySelector('#reset').onclick=()=>{v=[...original];draw()};
    s.addEventListener('wheel',e=>{e.preventDefault();const r=s.getBoundingClientRect();zoom(e.deltaY>0?1.15:.87,(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height)},{passive:false});
    s.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY,...v];s.setPointerCapture(e.pointerId)});
    s.addEventListener('pointermove',e=>{if(!drag)return;const r=s.getBoundingClientRect();v[0]=drag[2]-(e.clientX-drag[0])*v[2]/r.width;v[1]=drag[3]-(e.clientY-drag[1])*v[3]/r.height;draw()});
    s.addEventListener('pointerup',()=>drag=null);</script></body></html>'''
    return '<iframe title="벡터 결과 확대 보기" sandbox="allow-scripts" style="width:100%;height:580px;border:1px solid #d9e0e9;border-radius:10px" srcdoc="' + html.escape(document, quote=True) + '"></iframe>'


def infer(editor, round_lengths=False):
    image = editor.get('composite') if isinstance(editor, dict) else editor
    if image is None:
        raise gr.Error('준공도면을 업로드해 주세요.')
    if image.width * image.height > 60_000_000:
        raise gr.Error('이미지가 너무 큽니다. 전유부 영역을 잘라 다시 올려 주세요.')
    try:
        loaded = load()
        graph, shared, raw = predict(loaded, image, bool(round_lengths))
        folder = Path(tempfile.mkdtemp(prefix='img2dwg-shared-'))
        factory = exports(graph, folder)
        (folder / 'shared-graph.json').write_text(json.dumps(shared, ensure_ascii=False), encoding='utf-8')
        (folder / 'raw.svg').write_text(svg(compile_graph(raw, strict=False)), encoding='utf-8')
        counts = dict(collections.Counter(c['kind'] for c in shared['components']))
        release = loaded[-1]
        receipt = {**factory, 'model_repo': os.getenv('MODEL_REPO'),
            'model_revision': os.getenv('MODEL_REVISION'), 'model_sha256': release['model_sha256'],
            'deployment_role': release['deployment_role'], 'trained_real_pairs': release['trained_real_pairs'],
            'training_checkpoint_role': 'five-case-reproduction;not-full-training',
            'component_counts': counts, 'input_transform': graph['input_transform'],
            'normalized_input_pixels_sha256': graph['normalized_input_pixels_sha256'],
            'elapsed_seconds': graph['elapsed_seconds'], 'numeric_dimensions_verified': False,
            'vector_preview_contains_raster': False, 'source_CAD_or_dataset_access': False,
            'constraints': shared['constraint_receipt'], 'length_edit': shared.get('length_edit_receipt'),
            'unsupported_components': graph['unsupported_components'],
            'invalid_repeated_node_references': shared.get('invalid_repeated_references', 0)}
        (folder / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        # No fallback to GT, cached samples, a contour, or a line detector.
        raise gr.Error('변환을 완료하지 못했습니다. 도면을 다시 확인해 주세요. (' + type(exc).__name__ + ')') from exc
    status = f"**모델 벡터 초안 · {len(shared['components'])}개 컴포넌트 · {graph['elapsed_seconds']:.1f}초**\n\n"
    status += (f"벽 양면 {counts.get('wall_face_pair', 0)} · 문 {counts.get('swing_opening', 0)} · "
               f"사각 구조 {counts.get('rectangular_loop', 0)} · 치수 {counts.get('dimension', 0)}\n\n")
    status += '**5개 학습 사례 재현 모델이며, 별도 20개 검증은 미통과했습니다.** '
    status += 'mm는 모델이 예측한 CAD 좌표이며, 원본 도면의 실측 확인을 대신하지 않습니다.'
    residual = shared['constraint_receipt'].get('max_residual_mm')
    if residual is not None and residual > 1:
        status += f'\n\n치수 제약 충돌: 최대 {residual:.1f}mm. 치수의 연결 위치를 확인해 주세요.'
    if graph['unsupported_components']:
        status += f"\n\n출력하지 못한 컴포넌트 {len(graph['unsupported_components'])}개가 있습니다."
    if round_lengths:
        status += '\n\n벽·사각 컴포넌트의 1m 이상 길이에 100mm 보정을 적용했습니다. 치수 숫자·벽 두께·문 크기는 유지합니다.'
    return viewer(graph), status, str(folder / 'prediction.svg'), str(folder / 'prediction.dxf'), \
        str(folder / 'shared-graph.json'), str(folder / 'receipt.json'), str(folder / 'raw.svg')


with gr.Blocks(title='img2dwg · 컴포넌트 벡터 변환', theme=gr.themes.Soft(),
               delete_cache=(3600, 86400), analytics_enabled=False) as demo:
    gr.Markdown('# 도면 벡터 변환\n준공도면을 올리면 공유 노드 모델이 벽·문·치수 등의 벡터 초안을 생성합니다.')
    gr.Markdown('**5개 사례 재현 실험 모델 · 별도 20개 품질 검사 미통과**. 확대 가능한 SVG와 CAD에서 편집 가능한 DXF를 제공합니다.')
    with gr.Row():
        with gr.Column(scale=1):
            image = gr.ImageEditor(type='pil', image_mode='RGB', sources=['upload', 'clipboard'],
                transforms=['crop'], brush=False, eraser=False, layers=False,
                label='준공도면 · 필요하면 전유부 자르기', height=520, format='png')
            rounding = gr.Checkbox(value=False, label='주요 벽·사각 구조 길이 100mm 보정 (선택)')
            run = gr.Button('벡터 변환', variant='primary')
        with gr.Column(scale=1):
            preview = gr.HTML(label='벡터 결과')
            status = gr.Markdown('도면을 올리고 벡터 변환을 눌러 주세요.')
    with gr.Row():
        download_svg = gr.File(label='SVG · 확대 가능한 벡터')
        download_dxf = gr.File(label='DXF · 편집 가능한 CAD')
    with gr.Accordion('변환 기록과 보정 전 결과', open=False):
        download_graph = gr.File(label='컴포넌트 공유 그래프')
        download_receipt = gr.File(label='변환 기록')
        download_raw = gr.File(label='제약·길이 보정 전 SVG')
    run.click(infer, [image, rounding], [preview, status, download_svg, download_dxf,
        download_graph, download_receipt, download_raw], api_name='infer', concurrency_limit=1)
    gr.Markdown('DXF는 AutoCAD 등에서 열어 DWG로 저장할 수 있습니다. 현재 직접 다운로드 형식은 SVG·DXF입니다.')

if __name__ == '__main__':
    demo.queue(max_size=8).launch()
