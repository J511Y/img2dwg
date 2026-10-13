"""Render full source CAD with the selected crop rectangle for semantic review."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import ezdxf
from ezdxf.addons import odafc
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import BackgroundPolicy,ColorPolicy,Configuration
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend


def run(root:Path,source_module:Path,converter:Path):
    """Work only from saved local copies; never reopen original shares."""
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(source_module.parent.parent.parent))
    from data_pipeline.dwg_crop import pipeline as crop
    crop.configure_odafc(converter);crop.configure_matplotlib_fonts()
    for folder in sorted((root/'samples').iterdir()):
        p=folder/'report.json'
        if not p.exists() or (folder/'sheet-crop.png').exists():continue
        r=json.loads(p.read_text())
        if r['status']!='extracted_review_pending':continue
        if not (folder/'source.dxf').exists():
            doc=odafc.readfile(folder/'source.dwg',audit=False);doc.saveas(folder/'source.dxf')
        doc=ezdxf.readfile(folder/'source.dxf');rect=crop.layout_rect(doc.modelspace());x0,y0,x1,y1=r['crop']['bbox']
        fig=plt.figure(figsize=(16,10),dpi=100);ax=fig.add_axes([0,0,1,1])
        Frontend(RenderContext(doc),MatplotlibBackend(ax),config=Configuration(background_policy=BackgroundPolicy.WHITE,color_policy=ColorPolicy.BLACK)).draw_layout(doc.modelspace(),finalize=True)
        ax.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='red',linewidth=2))
        ax.set_xlim(rect.min_x,rect.max_x);ax.set_ylim(rect.min_y,rect.max_y);ax.set_aspect('equal');ax.set_axis_off();fig.savefig(folder/'sheet-crop.png',facecolor='white');plt.close(fig)
        print(folder.name,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source-module',type=Path,required=True);p.add_argument('--converter',type=Path,required=True);a=p.parse_args();run(a.root,a.source_module,a.converter)
