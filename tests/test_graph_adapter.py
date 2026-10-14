import unittest
import torch
from img2dwg.graph_decoder import SharedGraphDecoder
from img2dwg.graph_adapter import ProtectedGraphAdapter

class ProtectedGraphAdapterTests(unittest.TestCase):
    def make(self):
        torch.manual_seed(20261015);features=[torch.randn(1,4,768) for _ in range(5)]
        base=SharedGraphDecoder(12,10,hidden=48,coord_digits=8,measure_digits=6,minimum_nodes=4,minimum_components=4)
        model=ProtectedGraphAdapter(base,features,nodes=12,components=10,hidden=32)
        return model,features

    def test_original_feature_subspace_is_exactly_preserved_after_residual_changes(self):
        m,features=self.make()
        with torch.no_grad():
            for name,p in m.named_parameters():
                if not name.startswith('base.'):p.normal_(std=.2)
        for f in features:
            with torch.no_grad():a=m.base(f,capacities=[12,10]);b=m(f)
            for k in a:self.assertTrue(torch.equal(a[k],b[k]),k)
        self.assertTrue(all(not p.requires_grad for p in m.base.parameters()))

    def test_initial_adapter_does_not_alter_new_observation_and_can_learn(self):
        m,_=self.make();f=torch.randn(1,4,768)
        self.assertGreater(float(m.protected_features(f).norm()),1.)
        with torch.no_grad():a=m.base(f,capacities=[12,10]);b=m(f)
        for k in a:self.assertTrue(torch.equal(a[k],b[k]),k)
        out=m(f);out['xy'].sum().backward()
        self.assertGreater(float(m.node_heads['xy'].weight.grad.abs().sum()),0.)
        self.assertTrue(all(p.grad is None for p in m.base.parameters()))

    def test_prefix_count_crop_is_rejected_and_cache_matches_real_forward(self):
        m,_=self.make();f=torch.randn(1,4,768)
        with self.assertRaises(ValueError):m(f,capacities=[8,6])
        with torch.no_grad():base=m.base(f,capacities=[12,10]);cached=m(f,cached_base=base);real=m(f)
        for k in real:self.assertTrue(torch.equal(cached[k],real[k]),k)

    def test_inactive_spare_slots_preserve_original_decoded_components(self):
        from img2dwg.graph_decoder import decode
        from img2dwg.structured import TYPES
        torch.manual_seed(14);features=[torch.randn(1,4,768) for _ in range(5)]
        base=SharedGraphDecoder(36,26,hidden=48,minimum_nodes=4,minimum_components=4)
        with torch.no_grad():
            base.kind.weight.zero_();base.kind.bias.zero_();base.kind.bias[TYPES.index('centerline')]=30
            base.node_active.weight.zero_();base.node_active.bias.fill_(30)
        m=ProtectedGraphAdapter(base,features,nodes=36,components=26,hidden=32,base_capacity=[32,22])
        for f in features:
            with torch.no_grad():old=decode(base(f,capacities=[32,22]),['unknown']);new=decode(m(f),['unknown'])
            self.assertEqual(old['components'],new['components'])
            self.assertEqual(old['nodes_mm'],new['nodes_mm'][:32])

    def test_inference_load_needs_no_original_features_or_CAD(self):
        m,features=self.make();base=SharedGraphDecoder(12,10,hidden=48,coord_digits=8,measure_digits=6,minimum_nodes=4,minimum_components=4)
        loaded=ProtectedGraphAdapter(base,None,nodes=12,components=10,hidden=32,protected_rank=m.protected_rank)
        loaded.load_state_dict(m.state_dict())
        with torch.no_grad():a=m(features[0]);b=loaded(features[0])
        for k in a:self.assertTrue(torch.equal(a[k],b[k]),k)

    def test_zero_output_nonlinear_capacity_preserves_all_source_responses(self):
        source,features=self.make()
        with torch.no_grad():source.node_heads['xy'].weight.normal_(std=.1)
        base=SharedGraphDecoder(12,10,hidden=48,coord_digits=8,measure_digits=6,minimum_nodes=4,minimum_components=4)
        expanded=ProtectedGraphAdapter(base,None,nodes=12,components=10,hidden=32,protected_rank=source.protected_rank,query_nonlinear=True)
        missing,unexpected=expanded.load_state_dict(source.state_dict(),strict=False)
        self.assertFalse(unexpected);self.assertTrue(all(k.startswith(('node_refine.','component_refine.')) for k in missing))
        old_names=[k for k,p in source.named_parameters() if p.requires_grad]
        new_names=[k for k,p in expanded.named_parameters() if p.requires_grad]
        self.assertEqual(old_names,new_names[:len(old_names)])
        novel=torch.randn(1,4,768)
        for f in features+[novel]:
            with torch.no_grad():a=source(f);b=expanded(f)
            for k in a:self.assertTrue(torch.equal(a[k],b[k]),k)
        expanded(novel)['xy'].sum().backward()
        self.assertGreater(float(expanded.node_refine[-1].weight.grad.abs().sum()),0.)
        with torch.no_grad():
            expanded.node_refine[-1].weight.normal_(std=.2);expanded.component_refine[-1].weight.normal_(std=.2)
        for f in features:
            with torch.no_grad():a=source(f);b=expanded(f)
            for k in a:self.assertTrue(torch.equal(a[k],b[k]),k)
if __name__=='__main__':unittest.main()
