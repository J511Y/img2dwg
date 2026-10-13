import unittest
import numpy as np
from PIL import Image,ImageDraw
from img2dwg.grounding import baseline_graph,component_support,support_map

class GroundingTests(unittest.TestCase):
    def test_observed_lines_follow_input_and_are_not_model_predictions(self):
        image=Image.new('RGB',(128,128),'white'); ImageDraw.Draw(image).rectangle((20,20,100,100),outline='black',width=2)
        graph=baseline_graph(image,min_length=12)
        self.assertGreater(len(graph['components']),3)
        self.assertEqual(graph['geometry_source'],'observed-line-detection-baseline')
        self.assertTrue(all(c['kind']=='segment' for c in graph['components']))
        distance=support_map(image)
        self.assertTrue(all(component_support(c,distance)>.9 for c in graph['components']))
    def test_blank_input_has_no_fabricated_geometry(self):
        self.assertEqual(baseline_graph(Image.new('RGB',(128,128),'white'))['components'],[])
    def test_giant_nearly_collinear_arc_is_rejected(self):
        image=Image.new('RGB',(128,128),'white')
        c={'kind':'arc','points':[[20,50],[60,50.001],[100,50]]}
        self.assertEqual(component_support(c,support_map(image)),0)
    def test_unsupported_line_is_rejected(self):
        image=Image.new('RGB',(128,128),'white'); ImageDraw.Draw(image).line((10,20,110,20),fill='black',width=2)
        c={'kind':'segment','points':[[10,100],[110,100],[60,100]]}
        self.assertEqual(component_support(c,support_map(image)),0)
if __name__=='__main__': unittest.main()
