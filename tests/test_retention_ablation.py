import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
import torch
from safetensors.torch import save_file
from img2dwg.graph_decoder import SharedGraphDecoder,loss
from img2dwg.graph_transfer import initialize
from img2dwg.structured import prepare,encode


class RetentionAblationTests(unittest.TestCase):
    def target(self,offset=0):
        g={'schema':'img2dwg-vector/v1','canvas':[512,512],'scale':10.,'units':'mm','texts':[],
           'components':[{'kind':'segment','points':[[100+offset,100],[200+offset,100],[150+offset,100]],'role':0},
             {'kind':'dimension','points':[[100+offset,100],[200+offset,100],[150+offset,80]],'role':0,
              'measurement_mm':1000.,'dimension_kind':0,'angle_cad':0.}]}
        return {k:torch.from_numpy(v) for k,v in encode(prepare(g),{},coord_digits=8,measure_digits=6).items()}

    def test_explicit_capacity_allows_true_joint_adaptive_batch(self):
        m=SharedGraphDecoder(16,12,hidden=48,adaptive_capacity=True,minimum_nodes=4,minimum_components=4)
        f=torch.randn(2,4,768)
        with self.assertRaises(ValueError):m(f)
        p=m(f,capacities=[8,6]);self.assertEqual(tuple(p['xy'].shape),(2,8,2))
        self.assertEqual(tuple(p['kind'].shape[:2]),(2,6))

    def test_joint_and_accumulated_gradients_agree_without_update_frequency_change(self):
        torch.manual_seed(43);m=SharedGraphDecoder(8,6,hidden=48,coord_digits=8,measure_digits=6)
        f=torch.randn(2,4,768);targets=[self.target(),self.target(10)]
        v,_,_=loss(m(f),targets);v.backward()
        joint={k:p.grad.clone() for k,p in m.named_parameters() if p.grad is not None}
        m.zero_grad(set_to_none=True)
        for i in range(2):
            v,_,_=loss(m(f[i:i+1]),targets[i:i+1]);(v/2).backward()
        for k,p in m.named_parameters():
            if k in joint:self.assertTrue(torch.allclose(joint[k],p.grad,atol=3e-4,rtol=3e-4),k)

    def test_loss_override_only_removes_named_count_term(self):
        torch.manual_seed(44);m=SharedGraphDecoder(8,6,hidden=48,coord_digits=8,measure_digits=6)
        p=m(torch.randn(1,4,768));t=[self.target()]
        base,terms,matches=loss(p,t)
        zero,_,_=loss(p,t,matches,term_weights={'count':0})
        self.assertAlmostEqual(float(base-zero),terms['count'],places=4)
        same,_,_=loss(p,t,matches,term_weights={'count':1})
        self.assertEqual(float(base),float(same))
        zero.backward()
        for par in m.count.parameters():self.assertEqual(float(par.grad.abs().max()),0.)
        self.assertGreater(float(m.node_xy.weight.grad.abs().sum()),0.)

    def test_legacy_precision_never_discards_nonzero_digits(self):
        m=SharedGraphDecoder(8,6,hidden=48,coord_digits=8,measure_digits=6);t=self.target()
        loss(m(torch.randn(1,4,768)),[t],precision_digits=(6,5))
        t['node_digits'][0,0,0]=1
        with self.assertRaises(ValueError):loss(m(torch.randn(1,4,768)),[t],precision_digits=(6,5))

    def test_label_mapping_and_numeric_expansion_preserve_initializer(self):
        torch.manual_seed(45);old=SharedGraphDecoder(8,6,texts=2,hidden=48,templates=2)
        new=SharedGraphDecoder(12,10,texts=3,hidden=48,templates=3,coord_digits=8,measure_digits=6)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);save_file(old.state_dict(),str(root/'model.safetensors'))
            (root/'config.json').write_text(json.dumps({'texts':['unknown','room']}))
            (root/'library.json').write_text(json.dumps({'z':{}}))
            initialize(new,root/'model.safetensors',{'texts':['unknown','extra','room'],'library':{'a':{},'z':{}}})
        self.assertTrue(torch.equal(old.node_queries.weight,new.node_queries.weight[:8]))
        self.assertTrue(torch.equal(old.template.weight[1],new.template.weight[2]))
        self.assertTrue(torch.equal(old.text.weight[1],new.text.weight[2]))
        self.assertTrue(torch.equal(old.node_digits.weight.reshape(2,6,10,-1),new.node_digits.weight.reshape(2,8,10,-1)[:,-6:]))
        self.assertTrue(torch.all(new.node_digits.bias.reshape(2,8,10)[:,:2,0]==8))

    def test_comparison_pairs_change_only_the_declared_factor(self):
        import importlib.util
        p=Path(__file__).resolve().parents[1]/'scripts/train_retention_ablation.py'
        spec=importlib.util.spec_from_file_location('retention_runner',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        vs={v['name']:v for v in m.variants()}
        for a,b,expected in [('five-joint','five-online',{'batch'}),
          ('mixed-accumulate','mixed-variable-capacity',{'capacity'}),
          ('mixed-variable-capacity','mixed-count-loss-off',{'loss_weights'}),
          ('mixed-variable-capacity','mixed-legacy-digit-loss',{'precision_digits'}),
          ('mixed-variable-capacity','mixed-lower-lr',{'lr'}),
          ('mixed-variable-capacity','mixed-refresh-assignment',{'refresh_every'})]:
            diff={k for k in vs[a] if k!='name' and vs[a][k]!=vs[b][k]}
            self.assertEqual(diff,expected,(a,b))
if __name__=='__main__':unittest.main()
