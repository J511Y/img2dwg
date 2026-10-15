"""Load graph architectures from a pinned config; no CAD or identity inputs."""
from img2dwg.graph_decoder import SharedGraphDecoder
from img2dwg.graph_adapter import ProtectedGraphAdapter

def build_graph_model(config):
    c=config
    model=SharedGraphDecoder(c['nodes'],c['components'],len(c['texts']),hidden=c['hidden'],templates=c['templates'],
        coord_digits=c['coord_digits'],measure_digits=c['measure_digits'],adaptive_capacity=True,
        minimum_nodes=c['minimum_nodes'],minimum_components=c['minimum_components'])
    layers=c.get('adapter_stack') or ([c['adapter']] if c.get('adapter') else [])
    for layer in layers:
        model=ProtectedGraphAdapter(model,None,nodes=layer['nodes'],components=layer['components'],hidden=layer['hidden'],
            base_capacity=layer['base_capacity'],protected_rank=layer['protected_rank'],
            query_nonlinear=layer.get('query_nonlinear',False),padding_policy=layer.get('padding_policy','spatial'))
    return model
