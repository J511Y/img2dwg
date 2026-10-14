import unittest
import torch
from img2dwg.graph_decoder import SharedGraphDecoder,decode
from img2dwg.structured import TYPES

class ReferenceCandidateTests(unittest.TestCase):
    def observation(self):
        torch.manual_seed(8);model=SharedGraphDecoder(8,6,hidden=48)
        with torch.no_grad():pred=model(torch.randn(1,4,768))
        pred['xy'].fill_(.5);pred['xy'][0,0]=torch.tensor([0.,0.]);pred['xy'][0,1]=torch.tensor([.1,0.])
        pred['active'].fill_(-30);pred['active'][0,:3]=30
        pred['kind'].fill_(-30);pred['kind'][...,-1]=30
        pred['kind'][0,0,-1]=-30;pred['kind'][0,0,TYPES.index('centerline')]=30
        pred['anchors'][0,0,0]=torch.tensor([0.,0.]);pred['anchors'][0,0,1]=torch.tensor([.1,0.])
        pred['refs'][0,0].zero_();pred['refs'][0,0,:,2]=50
        return pred

    def test_distant_high_score_cannot_override_physical_anchor_candidates(self):
        pred=self.observation();before=pred['refs'].clone()
        baseline=decode(pred,['unknown']);resolved=decode(pred,['unknown'],reference_radius_mm=30)
        self.assertNotEqual(baseline['components'][0]['nodes'],[0,1])
        self.assertEqual(resolved['components'][0]['nodes'],[0,1])
        self.assertTrue(torch.equal(pred['refs'],before))
        self.assertEqual(resolved['reference_resolution_receipt']['unresolved_slots'],0)
        self.assertFalse(resolved['reference_resolution_receipt']['source_CAD_or_GT_access'])

    def test_missing_candidate_is_reported_without_inventing_nodes(self):
        pred=self.observation();pred['anchors'][0,0,0]=torch.tensor([.9,.9])
        resolved=decode(pred,['unknown'],reference_radius_mm=30)
        self.assertGreater(resolved['reference_resolution_receipt']['unresolved_slots'],0)
        self.assertEqual(len(resolved['nodes_mm']),8)
        with self.assertRaises(ValueError):decode(pred,['unknown'],reference_radius_mm=0)
if __name__=='__main__':unittest.main()
