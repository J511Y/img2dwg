import copy
import unittest
import numpy as np
import torch
import tempfile
from pathlib import Path
import ezdxf
from img2dwg.cad import extract
from img2dwg.structured import prepare,compile_graph,encode,TYPES
from img2dwg.graph_decoder import SharedGraphDecoder,assignments,loss,decode
from img2dwg.graph_constraints import project
from img2dwg.graph_evaluation import QualityStopper
from img2dwg.graph_evaluation import evaluate


class SharedGraphTests(unittest.TestCase):
    def graph(self):
        return {'schema':'img2dwg-vector/v1','canvas':[512,512],'scale':10.,'units':'mm','texts':[],
                'components':[{'kind':'segment','points':[[100,100],[200,100],[150,100]],'role':0,'source_id':'a'},
                              {'kind':'segment','points':[[200,100],[200,200],[200,150]],'role':0,'source_id':'b'},
                              {'kind':'dimension','points':[[100,100],[200,100],[150,80]],'role':0,'source_id':'d',
                               'measurement_mm':1000.,'dimension_kind':0,'angle_cad':0.}]}
    def test_shared_node_moves_every_referencing_component(self):
        b=prepare(self.graph()); before=compile_graph(b)
        node=next(i for i,p in enumerate(b['nodes_mm']) if np.allclose(p,[-560,-1560]))
        referencing=[c for c in b['components'] if node in c['nodes']]
        self.assertEqual(len(referencing),3)
        b['nodes_mm'][node][0]+=100
        after=compile_graph(b)
        self.assertEqual(sum(not np.allclose(a['points'],z['points']) for a,z in zip(before['components'],after['components'])),3)
    def test_targets_are_storage_order_invariant_sets(self):
        a=prepare(self.graph()); g=self.graph(); g['components'].reverse(); b=prepare(g)
        def signature(bundle):
            return sorted((c['kind'],tuple(np.asarray(bundle['nodes_mm'])[c['nodes']].ravel())) for c in bundle['components'])
        self.assertEqual(signature(a),signature(b))
    def test_prediction_only_constraint_updates_shared_geometry(self):
        b=prepare(self.graph()); b['components'][0]['parameters']['value_mm']=1100
        out=project(b); g=compile_graph(out)
        dim=next(c for c in g['components'] if c['kind']=='dimension')
        self.assertAlmostEqual(abs(dim['points'][1][0]-dim['points'][0][0])*g['scale'],1100,places=6)
        self.assertFalse(out['constraint_receipt']['source_CAD_or_GT_access'])
    def test_forward_backward_and_invalid_capacity(self):
        b=prepare(self.graph()); t={k:torch.from_numpy(v) for k,v in encode(b,{}).items()}
        m=SharedGraphDecoder(8,6,hidden=48); pred=m(torch.randn(1,4,768))
        value,_,_=loss(pred,[t]); value.backward(); self.assertTrue(torch.isfinite(value))
        small=SharedGraphDecoder(1,1,hidden=48)
        with self.assertRaises(ValueError): assignments(small(torch.randn(1,4,768)),t)
    def test_quality_stopping_and_plateau_are_separate_from_steps(self):
        s=QualityStopper(patience=2,stable_passes=2)
        self.assertEqual(s.update(.2,True)[0],'continue')
        self.assertEqual(s.update(.2,True)[0],'quality-passed')
        s=QualityStopper(patience=1)
        s.update(.1,False)
        self.assertEqual(s.update(.1,False)[0],'reduce-learning-rate')
        s.update(.1,False)
        self.assertEqual(s.update(.1,False)[0],'quality-plateau')
    def test_native_coincident_dimensions_are_not_geometry_deduplicated(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'source.dxf';doc=ezdxf.new('R2018');doc.units=4
            for _ in range(2):doc.modelspace().add_linear_dim(base=(500,800),p1=(200,200),p2=(1200,200),angle=0).render()
            doc.saveas(path);graph=extract(path,[0,0,2000,2000],512,min_length_pixels=0)
            self.assertEqual(sum(c['kind']=='dimension' for c in graph['components']),2)
    def test_component_matching_uses_all_shared_anchors_not_first_node(self):
        g=self.graph();g['components'][1]['points']=[[100,100],[100,200],[100,150]]
        truth=prepare(g);pred=copy.deepcopy(truth);pred['components'].reverse()
        for c in pred['components']:c['host']=-1
        a=compile_graph(pred);b=compile_graph(truth)
        metric=evaluate(pred,truth,a,b,{'audit_errors':0})
        self.assertEqual(metric['component_f1'],1.)
        self.assertEqual(metric['shared_reference_f1'],1.)
    def test_confident_axis_proposal_cannot_collapse_a_wall_thickness(self):
        b={'nodes_mm':[[0.,0.],[80.,0.]],'components':[],
           'axis_links':[[0,0],[0,1]],'axis_confidence':[[1.,1.],[1.,1.]]}
        out=project(b)
        self.assertEqual(out['nodes_mm'],b['nodes_mm'])
        self.assertEqual(out['constraint_receipt']['rejected_axis_proposals'],1)
    def test_numeric_refinement_must_agree_with_sign_and_geometry(self):
        m=SharedGraphDecoder(8,6,hidden=48);pred=m(torch.randn(1,4,768))
        pred['xy']=torch.full_like(pred['xy'],.0325)
        pred['node_digits']=torch.full_like(pred['node_digits'],-20.)
        for slot,digit in enumerate([0,0,3,2,5,0]):pred['node_digits'][...,slot,digit]=20.
        pred['node_sign']=torch.full_like(pred['node_sign'],-20.);pred['node_sign'][...,1]=20.
        decoded=decode(pred,['<unknown>'])
        # Even confident -325mm digits cannot replace the +325mm geometry.
        self.assertTrue(np.allclose(decoded['nodes_mm'],325.,atol=.001))
        self.assertEqual(decoded['high_confidence_0_1mm_coordinate_nodes'],0)

if __name__=='__main__': unittest.main()
