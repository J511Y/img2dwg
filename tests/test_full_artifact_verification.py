import json,tempfile,unittest
from pathlib import Path
from img2dwg.structured import compile_graph
from img2dwg.vector import exports
from scripts.verify_full_continuation import inspect_native

class NativeArtifactVerificationTests(unittest.TestCase):
    def test_native_origin_and_coincident_labels_are_order_independent(self):
        bundle={'frame':{'schema':'img2dwg-vector/v1','canvas':[512,512],'scale':10.,'units':'mm'},'nodes_mm':[[-1500,0],[1500,0],[0,300],[0,-300]],
            'components':[],'source':'image-model-prediction'}
        for i,value in enumerate([3000,3001]):
            bundle['components'].append({'id':'D'+str(i),'kind':'dimension','nodes':[0,1,2+i],
                'roles':[0],'host':-1,'parameters':{'value_mm':value,'angle_cad':0,'dimension_kind':0}})
        graph=compile_graph(bundle)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);factory=exports(graph,folder)
            (folder/'metrics.json').write_text(json.dumps({'passed':True,'factory':factory}))
            (folder/'shared-graph.json').write_text(json.dumps(bundle))
            graph['components'].reverse()
            (folder/'prediction.json').write_text(json.dumps(graph))
            result=inspect_native(folder)
            self.assertEqual(result['native_dimensions'],2)
            self.assertLess(result['native_dimension_anchor_max_delta_mm'],1e-6)
            self.assertEqual(result['native_dimension_label_geometry_max_delta_mm'],1.)

if __name__=='__main__':unittest.main()
