import copy,unittest
import torch
from img2dwg.graph_update import balanced_weights,coordinate_snapshot,guarded_step,maximum_movement
from img2dwg.graph_decoder import DEFAULT_LOSS_WEIGHTS

class GraphUpdateTests(unittest.TestCase):
    def test_balance_changes_only_continuous_group(self):
        weights,scale,categorical=balanced_weights(200,20)
        self.assertEqual(scale,.1);self.assertEqual(categorical,1.)
        for k,v in weights.items():self.assertAlmostEqual(v,DEFAULT_LOSS_WEIGHTS[k]*(.1 if k in ('node','proposal','parameter','dimension') else 1.))
        self.assertEqual(balanced_weights(1000,0)[1],.01)
        weights,scale,categorical=balanced_weights(10,80)
        self.assertEqual(scale,1.);self.assertEqual(categorical,.125)
        self.assertEqual(weights['numeric'],.125);self.assertEqual(weights['dimension'],4.)
        with self.assertRaises(ValueError):balanced_weights(float('nan'),1)

    def test_actual_digit_substitution_is_in_guard(self):
        xy=torch.tensor([[[.09995,0.]]]);digits=torch.full((1,1,2,5,10),-30.)
        for axis,value in enumerate(['10000','00000']):
            for i,d in enumerate(value):digits[0,0,axis,i,int(d)]=30.
        signs=torch.tensor([[[[30.,-30.],[30.,-30.]]]])
        pred={'xy':xy,'anchors':xy[:,:,None],'node_digits':digits,'node_sign':signs}
        s=coordinate_snapshot(pred)
        self.assertAlmostEqual(float(s['decoded_nodes_mm'][0,0,0]),1000)
        self.assertAlmostEqual(float(s['xy_mm'][0,0,0]),999.5)
        pred['xy']=torch.tensor([[[.09,0.]]]);self.assertAlmostEqual(float(coordinate_snapshot(pred)['decoded_nodes_mm'][0,0,0]),900,places=3)

    def test_guard_balance_matrix_is_single_factor(self):
        from scripts.train_guard_balance import variants
        v={x['name']:x for x in variants()}
        for left,right,field in [('control','coordinate-guard','coordinate_guard'),('control','loss-balance','gradient_balance'),
                                 ('coordinate-guard','guard-and-balance','gradient_balance'),('loss-balance','guard-and-balance','coordinate_guard')]:
            self.assertEqual({k for k in v[left] if k!='name' and v[left][k]!=v[right][k]},{field})

    def test_trust_region_scales_actual_nonlinear_output(self):
        model=torch.nn.Linear(1,1,bias=False);model.weight.data.fill_(1.)
        optimizer=torch.optim.SGD(model.parameters(),lr=1.)
        def capture():return {'old':{'xy_mm':model.weight.detach().square().reshape(1,1).clone()*100}}
        origin=capture();model.weight.grad=torch.ones_like(model.weight)*-1
        r=guarded_step(model,optimizer,capture,origin,['old'],step_mm=2.,retention_mm=10.)
        self.assertTrue(r['accepted']);self.assertLess(r['alpha'],1.)
        self.assertLessEqual(maximum_movement(origin,capture()),2.)

    def test_rejection_restores_adam_and_weights(self):
        model=torch.nn.Linear(1,1,bias=False);model.weight.data.fill_(1.)
        optimizer=torch.optim.Adam(model.parameters(),lr=.01)
        model.weight.grad=torch.ones_like(model.weight);optimizer.step()
        old=model.weight.detach().clone();state=copy.deepcopy(optimizer.state_dict())
        def capture():return {'old':{'xy_mm':model.weight.detach().reshape(1,1).clone()}}
        origin=capture();model.weight.grad=torch.ones_like(model.weight)
        r=guarded_step(model,optimizer,capture,origin,['old'],step_mm=0.,retention_mm=0.)
        self.assertFalse(r['accepted']);self.assertEqual(r['alpha'],0.)
        self.assertTrue(torch.equal(old,model.weight));new=optimizer.state_dict()
        for k in state['state']:
            for field in state['state'][k]:self.assertTrue(torch.equal(state['state'][k][field],new['state'][k][field]))

    def test_total_original_drift_is_bounded_across_updates(self):
        model=torch.nn.Linear(1,1,bias=False);model.weight.data.fill_(0.)
        optimizer=torch.optim.SGD(model.parameters(),lr=1.)
        def capture():return {'old':{'xy_mm':model.weight.detach().reshape(1,1).clone()}}
        origin=capture()
        for _ in range(4):
            model.weight.grad=torch.ones_like(model.weight)*-1
            guarded_step(model,optimizer,capture,origin,['old'],step_mm=1.,retention_mm=2.,backtracks=0)
        self.assertEqual(float(model.weight.detach()),2.)
if __name__=='__main__':unittest.main()
