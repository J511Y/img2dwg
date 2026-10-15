import unittest
import torch
from img2dwg.graph_decoder import SharedGraphDecoder
from img2dwg.graph_adapter import ProtectedGraphAdapter
from img2dwg.graph_loading import build_graph_model

class FullContinuationTests(unittest.TestCase):
    def test_package_rejects_same_processed_pixels_even_with_different_source_groups(self):
        import json,tempfile,sys
        from pathlib import Path
        from unittest.mock import patch
        from scripts.package_full_continuation import main
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=root/'data';data.mkdir()
            rows=[{'split':'train','input_sha256':'pixel-'+str(i),'group_id':'train-'+str(i)} for i in range(1028)]
            rows += [{'split':'validation','input_sha256':'dev-'+str(i),'group_id':'dev-'+str(i)} for i in range(16)]
            twenty=[{'split':'validation','input_sha256':'eval-'+str(i),'group_id':'eval-'+str(i)} for i in range(20)]
            twenty[0]['input_sha256']=rows[0]['input_sha256']
            (data/'index.json').write_text(json.dumps(rows));index=root/'eval.json';index.write_text(json.dumps(twenty))
            argv=['package','--data',str(data),'--holdout-source',str(data),'--evaluation-index',str(index),
                  '--release',str(root/'release'),'--remote-prefix','runs/test']
            with patch.object(sys,'argv',argv),self.assertRaises(AssertionError):main()

    def test_artifact_compaction_preserves_used_geometry_without_mutating_catalog(self):
        from scripts.train_retention_ablation import compact_bundle
        a={'nodes_mm':[[1,2]],'components':[{'kind':'native_symbol','parameters':{'template_id':'used'}}],
           'templates':{'used':[{'points':[[1,2]]}],'unused':[{'points':[[3,4]]}]}}
        b=compact_bundle(a)
        self.assertEqual(set(b['templates']),{'used'});self.assertEqual(b['templates']['used'],a['templates']['used'])
        self.assertEqual(b['components'],a['components']);self.assertEqual(len(a['templates']),2)

    def test_fitted_inner_adapter_is_preserved_by_outer_training(self):
        torch.manual_seed(54);old=[torch.randn(1,4,768) for _ in range(5)];additional=[torch.randn(1,4,768) for _ in range(5)]
        c=dict(nodes=20,components=18,texts=['?'],hidden=48,templates=1,coord_digits=8,measure_digits=6,minimum_nodes=8,minimum_components=6)
        base=build_graph_model(c)
        inner=ProtectedGraphAdapter(base,old,nodes=14,components=12,hidden=16,base_capacity=[10,8])
        with torch.no_grad():
            for n,p in inner.named_parameters():
                if not n.startswith('base.'):p.normal_(std=.1)
        outer=ProtectedGraphAdapter(inner,old+additional,nodes=22,components=20,hidden=16,base_capacity=[14,12],padding_policy='preserve-prefix')
        before={}
        with torch.no_grad():
            for i,f in enumerate(old+additional):before[i]=outer(f)
        novel=torch.randn(1,4,768);opt=torch.optim.Adam([p for p in outer.parameters() if p.requires_grad],lr=.01)
        for _ in range(3):
            opt.zero_grad();pred=outer(novel);pred['xy'].square().mean().backward();opt.step()
        for i,f in enumerate(old+additional):
            with torch.no_grad():now=outer(f);source=inner(f)
            for k in before[i]:self.assertTrue(torch.equal(before[i][k],now[k]),k)
            for k in source:
                if k in ('refs','host','axis'):continue
                self.assertTrue(torch.equal(now[k][(...,slice(None))] if k=='log_count' else now[k][:,:source[k].shape[1]],source[k]),k)
        self.assertTrue(all(not p.requires_grad for p in inner.parameters()))
        self.assertGreater(float(outer.protected_features(novel).norm()),1.)
        outer.eval()
        for f in old+additional:
            with torch.no_grad():a=outer(f);b=inner(f)
            for k in a:self.assertTrue(torch.equal(a[k],b[k]),k)

    def test_distance_equation_and_gradient_match_without_broadcast_temporary(self):
        a=torch.randn(1,3,12,2,dtype=torch.float64,requires_grad=True);b=torch.randn(1,7,2,dtype=torch.float64,requires_grad=True)
        old=(a[:,:,:,None]-b[:,None,None]).square().sum(-1);new=ProtectedGraphAdapter.squared_distance(a,b)
        self.assertTrue(torch.allclose(old,new,atol=1e-12,rtol=1e-12))
        g1=torch.autograd.grad(old.sum(),(a,b),retain_graph=True);g2=torch.autograd.grad(new.sum(),(a,b))
        for x,y in zip(g1,g2):self.assertTrue(torch.allclose(x,y,atol=1e-12,rtol=1e-12))

    def test_nested_stack_loads_without_protected_images_or_CAD(self):
        c=dict(nodes=20,components=18,texts=['?'],hidden=48,templates=1,coord_digits=8,measure_digits=6,minimum_nodes=8,minimum_components=6,
            adapter_stack=[dict(nodes=14,components=12,hidden=16,base_capacity=[10,8],protected_rank=4),dict(nodes=22,components=20,hidden=16,base_capacity=[14,12],protected_rank=9,padding_policy='preserve-prefix')])
        a=build_graph_model(c);b=build_graph_model(c);b.load_state_dict(a.state_dict())
        f=torch.randn(1,4,768)
        with torch.no_grad():one=a(f);two=b(f)
        for k in one:self.assertTrue(torch.equal(one[k],two[k]),k)

if __name__=='__main__':unittest.main()
