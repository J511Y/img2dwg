"""Frozen component topology and physical geometry evaluation."""
import numpy as np
from scipy.optimize import linear_sum_assignment
from img2dwg.raw_evaluation import evaluate_case

PROTOCOL={'geometry_tolerance_mm':10.,'dimension_tolerance_mm':1.,'minimum_structure_f1':.90,
          'minimum_component_f1':.95,'minimum_shared_reference_f1':.95,'required_dimension_coverage':1.,
          'required_unique_geometric_host_recall':1.,'invalid_node_references_allowed':0,
          'complete_business_semantics_claim':False,'checkpoint_selection_twenty_used':False,
          'matching_metric_version':'shared-component-set/v2;full-reference-cost-before-assignment'}


def evaluate(bundle,target_bundle,graph,target,factory):
    base=evaluate_case(graph,target,factory); a=bundle['components']; b=target_bundle['components']
    nodes=np.asarray(bundle['nodes_mm']); truth=np.asarray(target_bundle['nodes_mm'])
    pairs=[]; errors=[]
    for kind in sorted({c['kind'] for c in b}|{c['kind'] for c in a}):
        ia=[i for i,c in enumerate(a) if c['kind']==kind]; ib=[i for i,c in enumerate(b) if c['kind']==kind]
        if not ia or not ib:continue
        pa=np.array([nodes[a[i]['nodes'][0]] for i in ia]); pb=np.array([truth[b[i]['nodes'][0]] for i in ib])
        cost=np.linalg.norm(pa[:,None]-pb[None],axis=-1)
        # A shared first node is common (wall junctions, dimension chains). A
        # first-anchor-only assignment falsely swaps otherwise exact edges.
        cost.fill(1e9)
        for length in sorted({len(a[i]['nodes']) for i in ia}):
            ra=[r for r,i in enumerate(ia) if len(a[i]['nodes'])==length]
            cb=[c for c,i in enumerate(ib) if len(b[i]['nodes'])==length]
            if not cb:continue
            aa=np.asarray([nodes[a[ia[r]]['nodes']] for r in ra]); bb=np.asarray([truth[b[ib[c]]['nodes']] for c in cb])
            distances=np.linalg.norm(aa[:,None]-bb[None],axis=-1).max(-1)
            orders=[]
            if kind in ('unresolved_edge','centerline','symbol'):orders=[bb[:,::-1]]
            elif kind=='dimension':orders=[bb[:,[1,0,2]]]
            elif kind=='native_path':
                orders=[bb[:,::-1]]
                if all(b[ib[c]]['parameters']['closed'] for c in cb):
                    orders += [np.roll(bb,k,axis=1) for k in range(1,length)]
                    orders += [np.roll(bb[:,::-1],k,axis=1) for k in range(1,length)]
            for order in orders:distances=np.minimum(distances,np.linalg.norm(aa[:,None]-order[None],axis=-1).max(-1))
            if kind=='text':
                labels_a=np.asarray([a[ia[r]]['parameters']['text'] for r in ra]);labels_b=np.asarray([b[ib[c]]['parameters']['text'] for c in cb])
                distances+=np.not_equal.outer(labels_a,labels_b)*1e6
            elif kind=='native_symbol':
                labels_a=np.asarray([a[ia[r]]['parameters']['template_id'] for r in ra]);labels_b=np.asarray([b[ib[c]]['parameters']['template_id'] for c in cb])
                distances+=np.not_equal.outer(labels_a,labels_b)*1e-5
            cost[np.ix_(ra,cb)]=distances
        rr,cc=linear_sum_assignment(cost)
        for r,c in zip(rr,cc):
            x,y=ia[r],ib[c]; na=nodes[a[x]['nodes']]; nb=truth[b[y]['nodes']]
            error=float(cost[r,c])
            if kind=='text' and a[x]['parameters']['text']!=b[y]['parameters']['text']:error=float('inf')
            errors.append(error)
            if error<=10:pairs.append((x,y))
    component_f1=2*len(pairs)/(len(a)+len(b)) if a or b else 1.
    mapping={x:y for x,y in pairs}; inv={y:x for x,y in pairs}
    predicted=set(); expected=set()
    # Pairwise shared incidence includes edges, walls, dimensions and paths.
    for left,right in ((i,j) for i in mapping for j in mapping if i<j):
        if set(a[left]['nodes'])&set(a[right]['nodes']):predicted.add(tuple(sorted((mapping[left],mapping[right]))))
    incidences={}
    for i,c in enumerate(b):
        for node in c['nodes']:incidences.setdefault(node,[]).append(i)
    for members in incidences.values():
        expected.update((i,j) for i in members for j in members if i<j)
    hit=len(predicted&expected); relation_f1=2*hit/(len(predicted)+len(expected)) if predicted or expected else 1.
    hosts=[(i,c['host']) for i,c in enumerate(b) if c['host']>=0]
    host_hit=sum(i in inv and h in inv and a[inv[i]]['host']==inv[h] for i,h in hosts)
    host_recall=host_hit/len(hosts) if hosts else 1.
    bad=bundle.get('invalid_repeated_references',0)
    constraints=bundle.get('constraint_receipt',{}); residual=constraints.get('max_residual_mm')
    unsupported=len(graph.get('unsupported_components',[]))
    passed=(base['passed'] and component_f1>=.95 and relation_f1>=.95 and host_recall==1. and bad==0 and unsupported==0
            and (residual is None or residual<=1.))
    base.update(passed=bool(passed),component_f1=component_f1,shared_reference_f1=relation_f1,
                required_unique_geometric_hosts=len(hosts),correct_unique_geometric_hosts=host_hit,
                host_recall=host_recall,invalid_repeated_node_references=bad,
                node_anchor_median_error_mm=float(np.median([e for e in errors if np.isfinite(e)])) if errors else None,
                constraint_receipt=constraints,output_source='image-model-prediction')
    base['unsupported_components']=unsupported
    return base


class QualityStopper:
    """Quality pass/plateau, independently bounded by the job's wall clock."""
    def __init__(self,patience=5,min_delta=.002,stable_passes=2):
        self.patience=patience; self.min_delta=min_delta; self.stable_passes=stable_passes
        self.best=-float('inf'); self.stale=0; self.passes=0; self.reductions=0
    def update(self,score,all_pass):
        self.passes=self.passes+1 if all_pass else 0
        improved=score>self.best+self.min_delta
        if improved:self.best=score;self.stale=0
        else:self.stale+=1
        if self.passes>=self.stable_passes:return 'quality-passed',improved
        if self.stale>=self.patience:
            self.stale=0;self.reductions+=1
            return ('quality-plateau' if self.reductions>=3 else 'reduce-learning-rate'),improved
        return 'continue',improved
