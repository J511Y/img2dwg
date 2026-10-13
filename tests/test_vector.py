import unittest, tempfile
from pathlib import Path
import numpy as np
import ezdxf
from img2dwg.vector import arc_parameters, exports, svg, write_dxf

class VectorTests(unittest.TestCase):
    def fixture(self):
        return {'schema':'img2dwg-vector/v1','canvas':[100,100],'units':'mm','scale':10.,'components':[
            {'kind':'segment','points':[[10,20],[50,20],[30,20]],'role':1},
            {'kind':'arc','points':[[70,50],[64.1421356,64.1421356],[50,70]],'role':3},
            {'kind':'dimension','points':[[10,20],[50,20],[30,10]],'role':0,'value_text':'400','measurement_mm':400.}]}
    def test_real_svg_vector(self):
        output=svg(self.fixture())
        self.assertIn('<path',output); self.assertIn('viewBox=',output)
        for forbidden in ('<image','base64','foreignObject'): self.assertNotIn(forbidden,output)
    def test_metric_dimension_and_arc_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'x.dxf'; receipt=write_dxf(self.fixture(),path)
            self.assertEqual(receipt['units'],4); self.assertEqual(receipt['dimension_count'],1)
            self.assertLess(receipt['dimension_max_error_mm'],1e-6)
            doc=ezdxf.readfile(path); arc=doc.modelspace().query('ARC')[0]
            self.assertAlmostEqual(arc.dxf.radius,200,places=4)
            self.assertEqual(len(doc.modelspace().query('LINE')),1)
    def test_unknown_scale_not_mm(self):
        g=self.fixture(); g['units']='unitless'; g['components'][-1].pop('measurement_mm')
        g['components'][-1]['value_text']='?'
        with tempfile.TemporaryDirectory() as d:
            receipt=exports(g,Path(d)); self.assertEqual(receipt['units'],0)
            self.assertEqual(ezdxf.readfile(Path(d)/'prediction.dxf').modelspace().query('DIMENSION')[0].dxf.text,'?')
    def test_diagonal_arc_rejects_collinear(self):
        self.assertIsNone(arc_parameters([[0,0],[1,1],[2,2]]))
    def test_nan_rejected(self):
        g=self.fixture(); g['components'][0]['points'][0][0]=float('nan')
        with self.assertRaises(ValueError): svg(g)

if __name__=='__main__': unittest.main()
