"""Bounded first training run; saves checkpoints before evaluation and upload."""
from __future__ import annotations
import argparse, hashlib, json, os, random, sys, tarfile, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
from scipy.optimize import linear_sum_assignment
from torch.utils.data import Dataset, DataLoader
from safetensors.torch import save_file
from img2dwg.model import VectorModel, targets, loss, decode, BACKBONE, REVISION
from img2dwg.vector import KINDS, exports

class CADData(Dataset):
    def __init__(self,root,records,augment=False,size=768,slots=1,canonical=False):
        self.root=root; self.records=records; self.augment=augment; self.size=size
        self.slots=slots; self.canonical=canonical
        self.graphs={r['sample_id']:json.loads((root/r['sample_id']/'target.json').read_text()) for r in records}
        self.images={r['sample_id']:Image.open(root/r['sample_id']/'input.png').convert('RGB') for r in records}
    def __len__(self): return len(self.records)
    def __getitem__(self,index):
        key=self.records[index]['sample_id']; image=self.images[key].copy()
        graph=json.loads(json.dumps(self.graphs[key])); old=image.width
        if old!=self.size:
            image=image.resize((self.size,self.size),Image.Resampling.LANCZOS)
            for c in graph['components']: c['points']=(np.array(c['points'])*self.size/old).tolist()
        if self.augment:
            # Shared isometries preserve metric geometry and act on every component.
            if random.random()<.5:
                image=ImageOps.mirror(image)
                for c in graph['components']:
                    p=np.array(c['points']); p[:,0]=self.size-p[:,0]; c['points']=p.tolist()
            turns=random.randrange(4)
            for _ in range(turns):
                image=image.transpose(Image.Transpose.ROTATE_90)
                for c in graph['components']:
                    p=np.array(c['points']); c['points']=np.stack((p[:,1],self.size-p[:,0]),1).tolist()
            # Observation degradation, target stays canonical. No arbitrary geometry warp.
            if random.random()<.6:
                small=random.randint(self.size//2,self.size)
                image=image.resize((small,small),Image.Resampling.BILINEAR).resize((self.size,self.size),Image.Resampling.BILINEAR)
            if random.random()<.4: image=image.filter(ImageFilter.GaussianBlur(random.uniform(.1,.7)))
            if random.random()<.5: image=ImageEnhance.Contrast(image).enhance(random.uniform(.5,1.2))
        target,_,_=targets(graph,self.size,self.slots,self.canonical)
        array=np.asarray(image,dtype=np.float32)/255
        if self.augment: array=np.clip(array+np.random.normal(0,.015,array.shape),0,1).astype(np.float32)
        return torch.from_numpy(array.transpose(2,0,1).copy()),target

def component_metrics(pred,gt,tolerance=8.):
    results={}
    for kind in KINDS:
        a=np.array([c['points'] for c in pred if c['kind']==kind],dtype=float).reshape(-1,3,2)
        b=np.array([c['points'] for c in gt if c['kind']==kind],dtype=float).reshape(-1,3,2)
        matches=0; errors=[]
        if len(a) and len(b):
            inds=[0,2] if kind=='arc' else [0,1]
            x,y=a[:,inds],b[:,inds]
            direct=np.linalg.norm(x[:,None]-y[None],axis=-1).mean(-1)
            reverse=np.linalg.norm(x[:,None]-y[None,:,::-1],axis=-1).mean(-1)
            distance=np.minimum(direct,reverse)
            if kind in ('arc','dimension'):
                mid=1 if kind=='arc' else 2
                distance=np.maximum(distance,np.linalg.norm(a[:,None,mid]-b[None,:,mid],axis=-1))
            row,col=linear_sum_assignment(distance)
            valid=distance[row,col]<=tolerance; matches=int(valid.sum()); errors=distance[row[valid],col[valid]].tolist()
        results[kind]={'predicted':len(a),'target':len(b),'matched':matches,'matched_errors_px':errors}
    return results

@torch.inference_mode()
def evaluate(model,data,device,output,threshold,max_records):
    model.eval(); rows=[]
    for i in range(min(max_records,len(data))):
        image,_=data[i]; graph=decode(model(image[None].to(device)),data.size,threshold)
        key=data.records[i]['sample_id']; gt=data.graphs[key]['components']
        metrics=component_metrics(graph['components'],gt)
        rows.append({'sample_id':key,'metrics':metrics,'predicted_components':len(graph['components'])})
        if i<5: exports(graph,output/'validation-preview'/key)
    combined={}
    for kind in KINDS:
        values=[r['metrics'][kind] for r in rows]; p=sum(v['predicted'] for v in values); t=sum(v['target'] for v in values); m=sum(v['matched'] for v in values)
        precision=m/p if p else 0.; recall=m/t if t else 0.
        combined[kind]={'predicted':p,'target':t,'matched':m,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0.}
    result={'protocol':'unordered-component-mean-endpoint-and-arc-middle-or-dimension-label-position <=8px; Hungarian one-to-one',
        'coordinate_tolerance_px':8.,'resolution':data.size,'threshold':threshold,'records':len(rows),'aggregate':combined,'rows':rows,
        'domain':'synthetic-held-out-before-CAD;not-real-scan-accuracy','split_status':'exact-identity-separated;near-family-review-pending'}
    (output/'evaluation.json').write_text(json.dumps(result,indent=2)); model.train(); return result

def main():
    p=argparse.ArgumentParser(); p.add_argument('--data',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--steps',type=int,default=2500); p.add_argument('--batch',type=int,default=2); p.add_argument('--size',type=int,default=768)
    p.add_argument('--lr',type=float,default=3e-4); p.add_argument('--seed',type=int,default=20261013); p.add_argument('--threshold',type=float,default=.25)
    p.add_argument('--eval-records',type=int,default=64); p.add_argument('--model-repo'); p.add_argument('--tiny',type=int,default=0)
    p.add_argument('--slots',type=int,default=1); p.add_argument('--canonical-endpoints',action='store_true')
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.set_num_threads(4)
    if args.data.is_file():
        archive=args.data; args.data=Path('/tmp/img2dwg-training-data')
        args.data.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive) as f: f.extractall(args.data,filter='data')
    records=json.loads((args.data/'index.json').read_text()); train=[r for r in records if r['split']=='train']; val=[r for r in records if r['split']=='validation']
    if args.tiny: train=train[:args.tiny]
    if {r['group_id'] for r in train}&{r['group_id'] for r in val}: raise ValueError('Split identity overlap')
    training=CADData(args.data,train,augment=not args.tiny,size=args.size,slots=args.slots,canonical=args.canonical_endpoints)
    validation=CADData(args.data,val,size=args.size,slots=args.slots,canonical=args.canonical_endpoints)
    capacities=[targets(g,args.size,args.slots,args.canonical_endpoints)[1:] for g in training.graphs.values()]
    manifest={'args':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},'train_records':len(train),'validation_records':len(val),
        'backbone':BACKBONE,'backbone_revision':REVISION,'backbone_frozen':True,'target_centers_kept':sum(c[0] for c in capacities),
        'center_collisions_not_supervised':sum(c[1] for c in capacities),'numeric_dimension_ocr_trained':False,
        'source_archive_sha256':os.getenv('TRAINING_ARCHIVE_SHA256'),'code_sha256':os.getenv('CODE_SHA256')}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    device='cuda' if torch.cuda.is_available() else 'cpu'; print(json.dumps({'device':device,**manifest}),flush=True)
    model=VectorModel(slots=args.slots).to(device); opt=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=args.lr,weight_decay=.01)
    loader=DataLoader(training,batch_size=args.batch,shuffle=True,num_workers=0); iterator=iter(loader)
    enabled=device=='cuda'; amp_dtype=torch.bfloat16 if enabled and torch.cuda.is_bf16_supported() else torch.float32
    scaler=torch.amp.GradScaler('cuda',enabled=False)
    started=time.time(); losses=[]; exposures=set(); initial=None
    log=(args.output/'train.jsonl').open('a',encoding='utf-8')
    def save(step):
        state={k:v.detach().cpu().contiguous() for k,v in model.state_dict().items()}
        save_file(state,str(args.output/'model.safetensors'))
        config=model.encoder.config.to_dict(); config.pop('model_type',None)
        (args.output/'config.json').write_text(json.dumps({'schema':'img2dwg-vector-model/v1','architecture':'dinov3-frozen-dense-component-coordinate',
            'backbone_config':config,'size':args.size,'threshold':args.threshold,'kinds':KINDS,'completed_steps':step,'slots':args.slots,
            'dimension_values':'not-trained;unknown-until-human-or-OCR-confirmation'},indent=2))
    for step in range(1,args.steps+1):
        try: image,target=next(iterator)
        except StopIteration: iterator=iter(loader); image,target=next(iterator)
        image=image.to(device); target={k:v.to(device) for k,v in target.items()}; opt.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device,dtype=amp_dtype,enabled=enabled and amp_dtype==torch.bfloat16): pred=model(image); total,details=loss(pred,target)
        if not torch.isfinite(total): save(step-1); raise ValueError('Non-finite loss')
        scaler.scale(total).backward(); scaler.unscale_(opt); grad=torch.nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad),5.)
        if not torch.isfinite(grad): save(step-1); raise ValueError('Non-finite gradient')
        scaler.step(opt); scaler.update(); losses.append(float(total.detach()))
        if initial is None: initial=float(total.detach())
        if step==1 or step%25==0:
            row={'step':step,'loss':float(total.detach()),'mean_recent_loss':sum(losses[-25:])/len(losses[-25:]),**details,
                 'grad_norm':float(grad),'elapsed_seconds':time.time()-started,'cuda_peak_bytes':torch.cuda.max_memory_allocated() if enabled else 0}
            log.write(json.dumps(row)+'\n'); log.flush(); print(json.dumps(row),flush=True)
        if step%500==0: save(step)
    save(args.steps); log.close()
    result=evaluate(model,validation,device,args.output,args.threshold,args.eval_records)
    receipt={'status':'completed','steps':args.steps,'elapsed_seconds':time.time()-started,'initial_loss':initial,
             'last_100_mean_loss':sum(losses[-100:])/len(losses[-100:]),'model_sha256':hashlib.sha256((args.output/'model.safetensors').read_bytes()).hexdigest(),
             'evaluation':result['aggregate'],'quality_interpretation':'first synthetic baseline;real generalization and metric dimensions not established'}
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)); print(json.dumps(receipt),flush=True)
    if args.model_repo:
        from huggingface_hub import HfApi
        api=HfApi(token=os.environ.get('HF_TOKEN')); api.create_repo(args.model_repo,private=True,exist_ok=True)
        api.upload_folder(repo_id=args.model_repo,folder_path=args.output,allow_patterns=['model.safetensors','config.json','manifest.json','receipt.json','evaluation.json','train.jsonl'],commit_message='First bounded CAD synthetic component-coordinate training')
if __name__=='__main__': main()
