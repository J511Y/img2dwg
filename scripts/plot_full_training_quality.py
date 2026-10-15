"""Plot final logged loss separately from native CAD quality; no tuning."""
import argparse,hashlib,json,statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
    log=root/'job-stdout.log';history=root/'GPU/quality-history.json';receipt=root/'GPU/receipt.json'
    r=json.loads(receipt.read_text());h=json.loads(history.read_text())
    loss=[]
    for line in log.read_text(encoding='utf-8').splitlines():
        try:q=json.loads(line)
        except ValueError:continue
        if all(k in q for k in ('updates','loss','epoch','seconds')):loss.append(q)
    assert loss and h and r['execution_status']=='completed'
    selected=json.loads((root/'GPU/best-evaluation.json').read_text())['updates'] if r['selected_checkpoint']=='best.safetensors' else r['updates']
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    ax=axes[0,0];x=[z['updates'] for z in loss];y=[z['loss'] for z in loss]
    ax.scatter(x,y,s=7,alpha=.18,color='#537aaa',label='Every-25-update logged observations')
    median=[statistics.median(y[max(0,i-40):i+1]) for i in range(len(y))]
    ax.plot(x,median,color='#15498c',label='Trailing 41 logged-sample median')
    ax.set(title='Training loss (sampled; not a quality pass)',ylabel='Weighted graph loss');ax.legend(fontsize=7)
    xs=[z['updates'] for z in h]
    for group,label,color in [('retention','Protected TRAIN10','#17804f'),('development','Development16','#c93937'),('training_probe','TRAIN probe16','#b77912')]:
        rows=[z[group] for z in h]
        axes[0,1].plot(xs,[z['passed_cases'] for z in rows],marker='.',color=color,label=label)
        axes[1,0].plot(xs,[z['dimensions_correct_geometry_and_value']/max(1,z['required_dimensions']) for z in rows],marker='.',color=color,label=label)
        axes[1,1].plot(xs,[z['referenced_node_set_chamfer_mm'] for z in rows],marker='.',color=color,label=label)
    axes[0,1].set(title='Actual native CAD cases passing',ylabel='Passed cases',ylim=(-.5,16.5))
    axes[1,0].set(title='Required DIM: value and actual geometry jointly correct',ylabel='Joint DIM fraction',ylim=(-.03,1.03))
    axes[1,1].set(title='Only actual referenced nodes (unused reserve excluded)',ylabel='Symmetric node Chamfer (mm)')
    for ax in axes.flat:
        ax.axvline(selected,color='#703ea5',linestyle='--',alpha=.75,label='Selected checkpoint' if ax==axes[0,1] else None)
        for z in h:
            if z['action']=='reduce-learning-rate':ax.axvline(z['updates'],color='grey',linestyle=':',alpha=.6)
        ax.set_xlabel('Optimizer updates');ax.grid(alpha=.2)
    axes[0,1].legend(fontsize=8);axes[1,1].legend(fontsize=8)
    fig.suptitle('EXP-054: 1,028 pairs, frozen verified model + new pooled residual adapter\nProtected examples are retention, not generalization; no twenty cases used for selection',fontsize=12)
    for suffix in ('png','svg'):fig.savefig(root/('learning-quality.'+suffix),dpi=150)
    plt.close(fig)
    result={'schema':'actual-training-quality-plot/v1','model_sha256':r['model_sha256'],'selected_updates':selected,
        'total_updates':r['updates'],'logged_loss_observations':len(loss),'logged_loss_sampling':'every25 updates; different shuffled cases; not whole-dataset mean',
        'quality_history_records':len(h),'twenty_used':False,'loss_is_not_quality':True,
        'source_sha256':{p.relative_to(root).as_posix():sha(p) for p in (log,history,receipt)},
        'output_sha256':{n:sha(root/n) for n in ('learning-quality.png','learning-quality.svg')}}
    (root/'learning-quality.provenance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
