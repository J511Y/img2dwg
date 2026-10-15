"""An input-conditioned residual graph adapter with a protected input subspace.

The projection stores only frozen vision features, never CAD geometry or IDs.
All inference inputs go through the base model and trainable prediction heads.
The adapter's zero residual on the old feature subspace protects the old function;
it does not certify generalization, and never retrieves target CAD.
"""
import math
import torch
from torch import nn
from img2dwg.structured import MAX_REFS,PARAMS,TYPES

class ProtectedGraphAdapter(nn.Module):
    def __init__(self,base,original_features=None,*,nodes=1198,components=951,hidden=128,base_capacity=None,protected_rank=4,query_nonlinear=False,padding_policy='spatial'):
        super().__init__();self.base=base;self.base.requires_grad_(False)
        self.nodes=nodes;self.components=components;self.fixed_capacity=[nodes,components];self.hidden=hidden
        self.base_capacity=base_capacity or self.fixed_capacity
        if padding_policy not in ('spatial','preserve-prefix'):raise ValueError('Unknown padding policy')
        self.padding_policy=padding_policy
        if self.base_capacity[0]>nodes or self.base_capacity[1]>components:raise ValueError('Base reserve exceeds adapter reserve')
        width=base.image.in_features*2
        if original_features is None:
            rank=protected_rank;center=torch.zeros(width,dtype=torch.float64);basis=torch.zeros(width,rank,dtype=torch.float64)
        else:
            pooled=torch.cat([torch.cat((f.mean(1),f.amax(1)),-1) for f in original_features]).double()
            center=pooled.mean(0);_,s,vh=torch.linalg.svd(pooled-center,full_matrices=False)
            rank=int((s>s.max().clamp_min(1)*1e-10).sum());basis=vh[:rank].T.contiguous()
        self.register_buffer('protected_center',center);self.register_buffer('protected_basis',basis)
        self.protected_rank=rank;self.zero_tolerance=1e-4
        self.feature=nn.Linear(width,hidden,bias=False)
        self.node_queries=nn.Embedding(nodes,hidden);self.component_queries=nn.Embedding(components,hidden)
        nn.init.normal_(self.node_queries.weight,std=.1);nn.init.normal_(self.component_queries.weight,std=.1)
        self.node_shapes={'xy':(2,),'active':(),'node_digits':(2,base.coord_digits,10),'node_sign':(2,2)}
        self.component_shapes={'anchors':(MAX_REFS,2),'kind':(len(TYPES)+1,),'params':(PARAMS,),
            'role':(6,),'digits':(5,10),'text':(base.text.out_features,),'template':(base.template.out_features,),
            'bearing':(5,),'size_digits':(7,base.measure_digits,10),'size_sign':(7,2)}
        self.node_heads=nn.ModuleDict({k:nn.Linear(hidden,math.prod(shape),bias=False) for k,shape in self.node_shapes.items()})
        self.component_heads=nn.ModuleDict({k:nn.Linear(hidden,math.prod(shape),bias=False) for k,shape in self.component_shapes.items()})
        self.count=nn.Linear(hidden,2,bias=False)
        for head in [*self.node_heads.values(),*self.component_heads.values(),self.count]:nn.init.zeros_(head.weight)
        width=32;self.ref_q=nn.Linear(hidden,MAX_REFS*width,bias=False);self.ref_k=nn.Linear(hidden,width,bias=False)
        self.axis_q=nn.Linear(hidden,2*width,bias=False);self.axis_k=nn.Linear(hidden,2*width,bias=False)
        self.host_q=nn.Linear(hidden,width,bias=False);self.host_k=nn.Linear(hidden,width,bias=False)
        for head in [self.ref_q,self.axis_q,self.host_q]:nn.init.zeros_(head.weight)
        self.query_nonlinear=query_nonlinear
        if query_nonlinear:
            # Appended modules preserve the source parameter/Adam ordering.
            # Zero last layers preserve the entire initial function, including
            # novel inputs; no bias can create a residual on protected inputs.
            self.node_refine=nn.Sequential(nn.Linear(hidden,hidden*4,bias=False),nn.GELU(),nn.Linear(hidden*4,hidden,bias=False))
            self.component_refine=nn.Sequential(nn.Linear(hidden,hidden*4,bias=False),nn.GELU(),nn.Linear(hidden*4,hidden,bias=False))
            nn.init.zeros_(self.node_refine[-1].weight);nn.init.zeros_(self.component_refine[-1].weight)

    # Metadata delegates to the frozen decoder, allowing a second residual
    # branch without modifying the already fitted inner adapter/projection.
    @property
    def image(self):return self.base.image
    @property
    def text(self):return self.base.text
    @property
    def template(self):return self.base.template
    @property
    def coord_digits(self):return self.base.coord_digits
    @property
    def measure_digits(self):return self.base.measure_digits

    def protected_features(self,features):
        pooled=torch.cat((features.mean(1),features.amax(1)),-1).double()
        centered=pooled-self.protected_center
        residual=centered-(centered@self.protected_basis)@self.protected_basis.T
        norm=residual.norm(dim=-1,keepdim=True)
        residual=torch.where(norm<=self.zero_tolerance,torch.zeros_like(residual),residual)
        return residual.to(self.feature.weight.dtype)

    def forward(self,features,capacities=None,*,cached_base=None):
        if capacities is not None and list(capacities)!=self.fixed_capacity:
            raise ValueError('Unordered query inference uses the common fixed reserve, never a prefix count crop')
        self.base.eval()
        protected=self.protected_features(features)
        if self.padding_policy=='preserve-prefix' and not self.training and not torch.count_nonzero(protected):
            # Exact frozen response, selected by vision subspace, not case ID.
            # Avoid allocating an inactive full-size reserve for protected input.
            return self.base(features,capacities=self.base_capacity)
        if cached_base is None:
            with torch.no_grad():base=self.pad_base(self.base(features,capacities=self.base_capacity))
        else:base=cached_base
        phi=torch.tanh(self.feature(protected))
        n=self.node_queries.weight[None]*phi[:,None];c=self.component_queries.weight[None]*phi[:,None]
        if self.query_nonlinear:n=n+self.node_refine(n);c=c+self.component_refine(c)
        out=dict(base);b=features.shape[0]
        for source,heads,shapes,count in [(n,self.node_heads,self.node_shapes,self.nodes),(c,self.component_heads,self.component_shapes,self.components)]:
            for key,head in heads.items():
                delta=head(source).reshape(b,count,*shapes[key])
                out[key]=base[key]+delta*(.1 if key in ('xy','anchors') else 1.)
        # Rebase the distance bias while preserving the old logits exactly at zero residual.
        if self.padding_policy=='preserve-prefix':
            old_dist=self.squared_distance(base['anchors'],base['xy'].detach())
            new_dist=self.squared_distance(out['anchors'],out['xy'].detach())
        else:
            old_dist=(base['anchors'][:,:,:,None]-base['xy'].detach()[:,None,None]).square().sum(-1)
            new_dist=(out['anchors'][:,:,:,None]-out['xy'].detach()[:,None,None]).square().sum(-1)
        q=self.ref_q(c).reshape(b,self.components,MAX_REFS,-1);k=self.ref_k(n)
        out['refs']=base['refs']+400*(old_dist-new_dist)+torch.einsum('bcrd,bnd->bcrn',q,k)/math.sqrt(k.shape[-1])
        old_axis=(base['xy'].detach()[:,:,None]-base['xy'].detach()[:,None]).abs().permute(0,3,1,2)
        new_axis=(out['xy'].detach()[:,:,None]-out['xy'].detach()[:,None]).abs().permute(0,3,1,2)
        aq=self.axis_q(n).reshape(b,self.nodes,2,-1).transpose(1,2);ak=self.axis_k(n).reshape(b,self.nodes,2,-1).transpose(1,2)
        out['axis']=base['axis']+100*(old_axis-new_axis)+aq@ak.transpose(-1,-2)/math.sqrt(k.shape[-1])
        out['host']=base['host']+self.host_q(c)@self.host_k(c).transpose(-1,-2)/math.sqrt(k.shape[-1])
        out['log_count']=base['log_count']+self.count(phi)
        return out

    @staticmethod
    def squared_distance(anchors,xy):
        # Same squared Euclidean equation without a B*C*R*N*2 temporary.
        return anchors.square().sum(-1)[...,None]+xy.square().sum(-1)[:,None,None]-2*torch.einsum('bcrd,bnd->bcrn',anchors,xy)

    @torch.no_grad()
    def pad_base(self,base):
        """Add inactive, image-independent spare slots; never CAD-derived queries.

        Keeping the original base capacity avoids changing its feature context.
        The actual new graph uses the entire reserve and learned no-object flags.
        """
        n=base['xy'].shape[1];c=base['kind'].shape[1]
        if (n,c)==(self.nodes,self.components):return base
        b=base['xy'].shape[0];result={};device=base['xy'].device;dtype=base['xy'].dtype
        def grid(count):
            side=math.ceil(math.sqrt(max(1,count)))
            return torch.stack(torch.meshgrid(torch.linspace(-.8,.8,side,device=device,dtype=dtype),torch.linspace(-.8,.8,side,device=device,dtype=dtype),indexing='ij'),-1).reshape(-1,2)[:count]
        for key,shape in self.node_shapes.items():
            value=base[key].new_zeros((b,self.nodes,*shape));value[:,:n]=base[key];result[key]=value
        result['xy'][:,n:]=grid(self.nodes-n);result['active'][:,n:]=-4.
        for key,shape in self.component_shapes.items():
            value=base[key].new_zeros((b,self.components,*shape));value[:,:c]=base[key];result[key]=value
        result['anchors'][:,c:]=grid(self.components-c)[None,:,None]
        result['kind'][:,c:,-1]=4.
        distance=self.squared_distance(result['anchors'],result['xy']) if self.padding_policy=='preserve-prefix' else (result['anchors'][:,:,:,None]-result['xy'][:,None,None]).square().sum(-1)
        result['refs']=-400*distance;result['refs'][:,:c,:,:n]=base['refs']
        result['host']=base['host'].new_full((b,self.components,self.components),-12.)
        result['host'][:,:c,:c]=base['host']
        distance=(result['xy'][:,:,None]-result['xy'][:,None]).abs().permute(0,3,1,2)
        result['axis']=-100*distance-12.;result['axis'][:,:,:n,:n]=base['axis']
        # Spare nodes may initially represent themselves; all original axis logits remain intact.
        ids=torch.arange(n,self.nodes,device=device);result['axis'][:,:,ids,ids]=0.
        if self.padding_policy=='preserve-prefix':
            # New reserve slots cannot steal an old pointer at neutral init.
            # A finite margin allows supervised learning to use them later.
            result['refs'][:,:c,:,n:]=base['refs'].amax(-1,keepdim=True)-12.
            result['host'][:,:c,c:]=base['host'].amax(-1,keepdim=True)-12.
            result['axis'][:,:,:n,n:]=base['axis'].amax(-1,keepdim=True)-12.
            result['active'][:,n:]=base['active'].amin(-1,keepdim=True)-4.
            result['kind'][:,c:,-1]=4.
        result['log_count']=base['log_count']
        return result
