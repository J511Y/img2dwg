import unittest
import numpy as np
try:
    import torch
    from img2dwg.model import targets,decode
except ImportError:
    torch=None

@unittest.skipIf(torch is None,'Separate training runtime required')
class TargetTests(unittest.TestCase):
    def test_duplicate_centers_use_slots_instead_of_disappearing(self):
        graph={'components':[{'kind':'segment','points':[[20+i,30],[40-i,30],[30,30]],'role':0} for i in range(4)]}
        _,kept1,dropped1=targets(graph,128,1,True)
        _,kept4,dropped4=targets(graph,128,4,True)
        self.assertEqual((kept1,dropped1),(1,3)); self.assertEqual((kept4,dropped4),(4,0))
    def test_reversed_endpoints_have_identical_coordinate_supervision(self):
        a={'components':[{'kind':'segment','points':[[20,30],[40,30],[30,30]],'role':1}]}
        b={'components':[{'kind':'segment','points':[[40,30],[20,30],[30,30]],'role':1}]}
        ta,_,_=targets(a,128,4,True); tb,_,_=targets(b,128,4,True)
        self.assertTrue(torch.equal(ta['coords'],tb['coords']))
    def test_arc_direction_equivalence_preserves_midpoint(self):
        a={'components':[{'kind':'arc','points':[[20,30],[30,40],[40,30]],'role':3}]}
        b={'components':[{'kind':'arc','points':[[40,30],[30,40],[20,30]],'role':3}]}
        ta,_,_=targets(a,128,4,True); tb,_,_=targets(b,128,4,True)
        self.assertTrue(torch.equal(ta['coords'],tb['coords']))
    def test_spatial_node_bins_match_original_first_neighbor_graph(self):
        pred={'centers':torch.full((1,16,32,32),-100.),'coords':torch.zeros(1,16,6,32,32),'roles':torch.zeros(1,16,6,32,32)}
        for channel,x,p,confidence in [(0,7,[[20,20],[40,20],[30,20]],4.),(1,12,[[40.5,20],[60,20],[50.25,20]],3.)]:
            pred['centers'][0,channel,5,x]=confidence
            pred['coords'][0,channel,:,5,x]=torch.tensor((np.array(p)-[(x+.5)*4,22]).ravel()/128,dtype=torch.float32)
        graph=decode(pred,128,threshold=.5)
        self.assertEqual(len(graph['nodes']),3); self.assertEqual(graph['edges'],[[0,1],[1,2]])
    def test_semicircles_with_same_endpoints_are_both_retained(self):
        pred={'centers':torch.full((1,16,32,32),-100.),'coords':torch.zeros(1,16,6,32,32),'roles':torch.zeros(1,16,6,32,32)}
        for channel,p,confidence in [(4,[[20,40],[40,20],[60,40]],4.),(5,[[20,40],[40,60],[60,40]],3.)]:
            pred['centers'][0,channel,10,10]=confidence
            pred['coords'][0,channel,:,10,10]=torch.tensor((np.array(p)-[42,42]).ravel()/128,dtype=torch.float32)
        graph=decode(pred,128,threshold=.5)
        self.assertEqual(len(graph['components']),2); self.assertTrue(all(c['kind']=='arc' for c in graph['components']))

if __name__=='__main__': unittest.main()
