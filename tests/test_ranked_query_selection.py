import math,unittest
import torch
from img2dwg.graph_decoder import SharedGraphDecoder,decode
from img2dwg.structured import TYPES

class RankedQueryTests(unittest.TestCase):
    def observation(self):
        torch.manual_seed(6);m=SharedGraphDecoder(8,6,hidden=48)
        with torch.no_grad():p=m(torch.randn(1,4,768))
        p['xy'].zero_();p['xy'][0,1,0]=.1
        p['active'].fill_(-30);p['active'][0,0]=50;p['active'][0,1]=49
        p['kind'].fill_(-40);p['kind'][...,-1]=40
        # Both foreground probabilities saturate at 1. Log odds still rank the
        # genuine late query above a phantom early dimension, without GT input.
        p['kind'][0,0,-1]=0;p['kind'][0,0,TYPES.index('dimension')]=30
        p['kind'][0,4,-1]=0;p['kind'][0,4,TYPES.index('centerline')]=80
        p['refs'][0,4].zero_();p['refs'][0,4,0,0]=50;p['refs'][0,4,1,1]=50
        p['log_count'][0]=torch.tensor([math.log(2),math.log(1)])
        return p

    def test_ranked_set_selects_late_query_and_removes_untrained_dimension(self):
        p=self.observation();baseline=decode(p,['unknown'])
        ranked=decode(p,['unknown'],set_selection='image-count-topk')
        self.assertEqual(len(baseline['components']),2)
        self.assertEqual([c['id'] for c in ranked['components']],['Q0004'])
        self.assertEqual(ranked['components'][0]['nodes'],[0,1])
        self.assertEqual(ranked['query_selection_receipt']['predicted_counts_rounded'],[2,1])
        self.assertFalse(ranked['query_selection_receipt']['source_CAD_or_GT_access'])

    def test_unavailable_capacity_and_invalid_forecast_are_reported(self):
        p=self.observation();p['log_count'][0]=torch.tensor([math.log(20),math.log(10)])
        ranked=decode(p,['unknown'],set_selection='image-count-topk')
        self.assertTrue(ranked['query_selection_receipt']['capacity_limited'])
        p['log_count'][0,0]=float('inf')
        with self.assertRaises(ValueError):decode(p,['unknown'],set_selection='image-count-topk')

    def test_inconsistent_high_confidence_dimension_is_not_a_hard_constraint(self):
        p=self.observation()
        p['kind'][0,0,TYPES.index('dimension')]=100
        p['digits'][0,0].fill_(-30)
        for i,d in enumerate([9,9,9,9,9]):p['digits'][0,0,i,d]=30
        p['log_count'][0,1]=math.log(1)
        unguarded=decode(p,['unknown'],set_selection='image-count-topk')
        self.assertEqual(unguarded['components'][0]['kind'],'dimension')
        guarded=decode(p,['unknown'],set_selection='image-count-topk',dimension_consistency_mm=10)
        self.assertEqual(guarded['components'][0]['id'],'Q0004')
        self.assertEqual(len(guarded['query_selection_receipt']['rejected_dimension_candidates']),1)
        self.assertGreater(guarded['query_selection_receipt']['rejected_dimension_candidates'][0]['residual_mm'],10)
if __name__=='__main__':unittest.main()
