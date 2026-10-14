import copy
import tempfile
import unittest
from pathlib import Path
import ezdxf
import numpy as np
from img2dwg.components import assemble, prepare_components, to_mm
from img2dwg.vector import write_dxf


class ComponentFactoryTests(unittest.TestCase):
    def test_rectangles_are_real_reusable_block_instances(self):
        frame = {'schema': 'img2dwg-vector/v1', 'canvas': [10000, 10000], 'scale': 1, 'units': 'mm'}
        components = [{'id': f'R{i}', 'kind': 'rectangular_loop', 'roles': [0] * 4,
            'parameters': {'center_mm': [i * 3000, 0], 'width_mm': 1000 * (i + 1),
                           'height_mm': 500, 'angle_degrees': 0}} for i in range(2)]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'components.dxf'
            write_dxf(assemble({'frame': frame, 'components': components}), path)
            doc = ezdxf.readfile(path); instances = list(doc.modelspace().query('INSERT'))
            self.assertEqual(len(instances), 2)
            self.assertEqual(instances[0].dxf.name, instances[1].dxf.name)
            self.assertEqual(instances[1].dxf.xscale, instances[0].dxf.xscale * 2)
            self.assertEqual(instances[0].get_xdata('IMG2DWG_COMPONENT')[0].value, 'rectangular_loop')

    def test_door_width_controls_leaf_and_arc_together(self):
        component = {'id': 'door', 'kind': 'swing_opening', 'roles': [3, 3],
            'parameters': {'hinge_mm': [0, 0], 'radius_mm': 800, 'start_degrees': 0,
                'extent_degrees': 90, 'sweep': 1, 'leaf_hinge_offset_ratio': [0, 0],
                'leaf_length_ratio': 1, 'leaf_at': 0, 'leaf_angle_offset_degrees': 0}}
        bundle = {'frame': {'schema': 'img2dwg-vector/v1', 'canvas': [2000, 2000], 'scale': 1, 'units': 'mm'},
                  'components': [component]}
        graph = assemble(bundle)
        self.assertAlmostEqual(np.linalg.norm(to_mm(graph['components'][1]['points'], graph)[1]), 800)
        component['parameters']['radius_mm'] = 900
        graph = assemble(bundle)
        self.assertAlmostEqual(np.linalg.norm(to_mm(graph['components'][1]['points'], graph)[1]), 900)
        self.assertAlmostEqual(np.linalg.norm(to_mm(graph['components'][0]['points'], graph)[0]), 900)

    def test_wall_thickness_moves_both_faces_about_spine(self):
        bundle = {'frame': {'schema': 'img2dwg-vector/v1', 'canvas': [2000, 2000], 'scale': 1, 'units': 'mm'},
            'components': [{'id': 'wall', 'kind': 'wall_face_pair', 'roles': [2, 2], 'parameters':
                {'spine_origin_mm': [0, 0], 'angle_degrees': 0, 'thickness_mm': 200,
                 'face_extents_mm': [[-500, 500], [-500, 500]], 'face_signs': [-1, 1]}}]}
        graph = assemble(bundle)
        a, b = [to_mm(c['points'], graph)[0, 1] for c in graph['components']]
        self.assertEqual(b - a, 200)
        bundle['components'][0]['parameters']['thickness_mm'] = 300
        graph = assemble(bundle)
        a, b = [to_mm(c['points'], graph)[0, 1] for c in graph['components']]
        self.assertEqual(b - a, 300)

    def test_dimension_and_unknown_geometry_are_not_dropped(self):
        graph = {'schema': 'img2dwg-vector/v1', 'canvas': [2000, 2000], 'scale': 1, 'units': 'mm',
            'components': [{'kind': 'dimension', 'points': [[100, 100], [1100, 100], [500, 50]],
                'role': 1, 'measurement_mm': 1000, 'dimension_kind': 0, 'angle_cad': 0},
                {'kind': 'segment', 'points': [[20, 30], [50, 70], [35, 50]], 'role': 0}]}
        bundle = prepare_components(graph); rebuilt = assemble(bundle)
        self.assertEqual(len(rebuilt['components']), 2)
        self.assertEqual(bundle['components'][1]['kind'], 'unresolved_residual')
        self.assertFalse(rebuilt['model_restoration'])
        self.assertEqual(rebuilt['components'][0]['measurement_mm'], 1000)
