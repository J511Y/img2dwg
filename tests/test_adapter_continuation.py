import copy,unittest
import torch
from scripts.train_protected_adapter import restore_adapter_optimizer

class ContinuationTests(unittest.TestCase):
    def test_new_capacity_starts_its_own_adam_state_and_preserves_old_moments(self):
        model=torch.nn.Linear(3,2);opt=torch.optim.Adam(model.parameters(),lr=.003)
        model(torch.ones(1,3)).sum().backward();opt.step()
        snapshot={'optimizer':copy.deepcopy(opt.state_dict()),'matches':{},'epoch':1}
        extended=torch.nn.Sequential(copy.deepcopy(model),torch.nn.Linear(2,2))
        restored,_=restore_adapter_optimizer(extended,snapshot,.0003,'cpu')
        old=list(extended[0].parameters());new=list(extended[1].parameters())
        self.assertEqual(int(restored.state[old[0]]['step']),1)
        self.assertNotIn(new[0],restored.state)
        extended(torch.ones(1,3)).sum().backward();restored.step()
        self.assertEqual(int(restored.state[old[0]]['step']),2)
        self.assertEqual(int(restored.state[new[0]]['step']),1)
        self.assertEqual(len(snapshot['optimizer']['param_groups'][0]['params']),2)

    def test_resumed_adam_matches_uninterrupted_update_at_new_rate(self):
        torch.manual_seed(17);model=torch.nn.Linear(3,2)
        optimizer=torch.optim.Adam(model.parameters(),lr=.003)
        x=torch.randn(4,3);target=torch.randn(4,2)
        for _ in range(7):
            optimizer.zero_grad();(model(x)-target).square().mean().backward();optimizer.step()
        snapshot={'optimizer':copy.deepcopy(optimizer.state_dict()),'matches':{'train':(torch.tensor([1,0]),torch.tensor([0,1]))},'epoch':7}
        resumed=copy.deepcopy(model);other,matches=restore_adapter_optimizer(resumed,snapshot,.0001,'cpu')
        for group in optimizer.param_groups:group['lr']=.0001
        for m,opt in [(model,optimizer),(resumed,other)]:
            opt.zero_grad();(m(x)-target).square().mean().backward();opt.step()
        for a,b in zip(model.parameters(),resumed.parameters()):self.assertTrue(torch.equal(a,b))
        self.assertEqual(snapshot['optimizer']['param_groups'][0]['lr'],.003)
        self.assertEqual(int(next(iter(other.state.values()))['step']),8)
        matches['train'][0][0]=9;self.assertEqual(int(snapshot['matches']['train'][0][0]),1)
        second,_=restore_adapter_optimizer(resumed,snapshot,.0003,'cpu')
        self.assertEqual(int(next(iter(second.state.values()))['step']),7)
if __name__=='__main__':unittest.main()
