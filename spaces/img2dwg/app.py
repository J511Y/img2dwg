"""Private upload-to-vector demo. No retrieval or ground-truth CAD at inference."""
import collections, hashlib, html, json, os, tempfile, threading
from pathlib import Path
import gradio as gr
import torch
from huggingface_hub import snapshot_download
from img2dwg.inference import load_checkpoint,predict,normalize_image
from img2dwg.grounding import baseline_graph
from img2dwg.vector import exports,svg

torch.set_num_threads(int(os.getenv('TORCH_THREADS','2')))
MODEL=None; CONFIG=None; SHA=None; LOCK=threading.Lock()
def load():
    global MODEL,CONFIG,SHA
    if MODEL is None:
        with LOCK:
            if MODEL is None:
                directory=os.getenv('LOCAL_MODEL_DIR') or snapshot_download(
                    os.getenv('MODEL_REPO','youjunhyeok/img2dwg-vector-first-v2'),
                    revision=os.environ['MODEL_REVISION'],allow_patterns=['model.safetensors','config.json'])
                MODEL,CONFIG,SHA=load_checkpoint(directory,os.getenv('MODEL_SHA256'))
    return MODEL,CONFIG,SHA

def viewer(graph):
    document='''<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;background:#f1f5f9;font:14px sans-serif}nav{padding:8px;display:flex;gap:8px;align-items:center}
    button{border:1px solid #ccd2db;border-radius:5px;background:white;padding:5px 12px;cursor:pointer}
    #view{height:520px;background:white;cursor:grab;overflow:hidden}svg{display:block;width:100%;height:100%}
    </style></head><body><nav><button id="plus">＋</button><button id="minus">－</button><button id="reset">전체</button>
    <span>휠로 확대 · 드래그로 이동</span></nav><div id="view">'''+svg(graph)+'''</div><script>
    const s=document.querySelector('svg'),original=s.getAttribute('viewBox').split(' ').map(Number);let v=[...original],drag=null;
    function draw(){s.setAttribute('viewBox',v.join(' '))}function zoom(f,x=.5,y=.5){v=[v[0]+v[2]*x*(1-f),v[1]+v[3]*y*(1-f),v[2]*f,v[3]*f];draw()}
    document.querySelector('#plus').onclick=()=>zoom(.8);document.querySelector('#minus').onclick=()=>zoom(1.25);
    document.querySelector('#reset').onclick=()=>{v=[...original];draw()};
    s.addEventListener('wheel',e=>{e.preventDefault();const r=s.getBoundingClientRect();zoom(e.deltaY>0?1.15:.87,(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height)},{passive:false});
    s.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY,...v];s.setPointerCapture(e.pointerId)});
    s.addEventListener('pointermove',e=>{if(!drag)return;const r=s.getBoundingClientRect();v[0]=drag[2]-(e.clientX-drag[0])*v[2]/r.width;v[1]=drag[3]-(e.clientY-drag[1])*v[3]/r.height;draw()});
    s.addEventListener('pointerup',()=>drag=null);</script></body></html>'''
    return '<iframe title="벡터 결과 확대 보기" sandbox="allow-scripts" style="width:100%;height:580px;border:1px solid #d9e0e9;border-radius:10px" srcdoc="'+html.escape(document,quote=True)+'"></iframe>'

def infer(editor,width_mm,threshold):
    image=editor.get('composite') if isinstance(editor,dict) else editor
    if image is None: raise gr.Error('도면을 업로드해 주세요.')
    if image.width*image.height>60_000_000: raise gr.Error('이미지가 너무 큽니다. 전유부 영역을 잘라 다시 올려 주세요.')
    # The coordinate model failed on real scans. Do not publish it as conversion.
    import time
    started=time.perf_counter()
    canvas,transform=normalize_image(image,768)
    graph=baseline_graph(canvas,min_length=max(8,min(64,float(threshold))))
    graph['model_status']='coordinate-model-rejected-on-real-input'
    graph['model_sha256']=None
    graph['input_transform']=transform
    graph['elapsed_seconds']=time.perf_counter()-started
    if width_mm and width_mm>0:
        graph['scale']=float(width_mm)/transform['fitted_size'][0]; graph['units']='mm'
        graph['scale_authority']='user-confirmed-width;no-dimension-solver'
    sha=None
    folder=Path(tempfile.mkdtemp(prefix='img2dwg-'))
    receipt=exports(graph,folder)
    receipt.update({'model_sha256':sha,'elapsed_seconds':graph['elapsed_seconds'],
        'component_counts':dict(collections.Counter(c['kind'] for c in graph['components'])),
        'vector_preview_contains_raster':False,'numeric_dimensions_verified':False})
    (folder/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    counts=receipt['component_counts']
    status=f"**원본 선 검출 기준선 · {len(graph['components'])}개 선분 · {graph['elapsed_seconds']:.1f}초**\n\n"
    status+='기존 학습 모델은 실제 스캔에서 복원에 실패해 기본 출력에서 제외했습니다. **이 결과는 학습 모델의 CAD 복원 결과가 아닙니다.**\n\n'
    status+='선분 '+str(counts.get('segment',0))+' · 곡선 '+str(counts.get('arc',0))+' · 치수 후보 '+str(counts.get('dimension',0))+'\n\n'
    status+='축척: '+('선택한 이미지의 전체 폭을 기준으로 mm 적용.' if graph['units']=='mm' else '미확정. DXF는 단위 없음으로 저장됩니다.')
    status+=' **중심선·치수·문·벽 컴포넌트 복원은 아직 완료하지 않았습니다.**'
    if not graph['components']: status+='\n\n객체를 찾지 못했습니다. 전유부를 더 크게 잘라 올리거나 검출 기준을 낮춰 보세요.'
    return viewer(graph),status,str(folder/'prediction.svg'),str(folder/'prediction.dxf'),str(folder/'prediction.json'),str(folder/'receipt.json')

with gr.Blocks(title='img2dwg · 복원 실패 진단',theme=gr.themes.Soft(),delete_cache=(3600,86400),analytics_enabled=False) as demo:
    gr.Markdown('# 도면 복원 실험\n**1차 좌표 예측 모델은 실제 스캔 복원에 실패했습니다. 기본 사용을 중단하고 개선 중입니다.**')
    gr.Markdown('아래는 입력에서 실제로 검출한 선을 확인하는 기하 기준선입니다. 치수에 맞는 CAD 복원 결과가 아닙니다.')
    with gr.Row():
        with gr.Column(scale=1):
            image=gr.ImageEditor(type='pil',image_mode='RGB',sources=['upload','clipboard'],transforms=['crop'],
                brush=False,eraser=False,layers=False,label='준공도면 · 자르기로 전유부 선택',height=520,format='png')
            gr.Markdown('업로드 후 **Image → Crop → Confirm crop**으로 전유부를 선택할 수 있습니다.')
            width=gr.Number(value=0,minimum=0,label='선택한 이미지 전체 폭의 실제 길이 (mm, 모르면 0)',precision=1)
            with gr.Accordion('선 검출 설정',open=False): threshold=gr.Slider(8,64,value=12,step=1,label='최소 선분 길이 (px)')
            run=gr.Button('원본 선 구조 확인',variant='primary')
        with gr.Column(scale=1):
            preview=gr.HTML(label='벡터 결과'); status=gr.Markdown('도면을 올리면 여기에 결과가 표시됩니다.')
    with gr.Row():
        download_svg=gr.File(label='SVG · 관측 선 기준선'); download_dxf=gr.File(label='DXF · 관측 선 기준선')
    with gr.Accordion('변환 기록',open=False):
        download_json=gr.File(label='벡터 좌표'); download_receipt=gr.File(label='검증 기록')
    run.click(infer,[image,width,threshold],[preview,status,download_svg,download_dxf,download_json,download_receipt],api_name='infer',concurrency_limit=1)
    gr.Markdown('DXF는 AutoCAD 등에서 열어 DWG로 저장할 수 있습니다. 현재 서비스의 직접 다운로드 형식은 SVG·DXF입니다.')
if __name__=='__main__': demo.queue(max_size=8).launch()
