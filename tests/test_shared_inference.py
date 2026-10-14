import copy
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from img2dwg.inference import normalize_image
from img2dwg.shared_inference import normalize, load
from img2dwg.graph_constraints import snap_major_lengths


class SharedInferenceTests(unittest.TestCase):
    def test_normalization_matches_real_training(self):
        image = Image.new('RGBA', (937, 1283), (10, 20, 30, 64))
        expected, expected_transform = normalize_image(image, 512)
        actual, actual_transform = normalize(image, 512)
        self.assertEqual(actual.tobytes(), expected.tobytes())
        self.assertEqual(actual_transform, expected_transform)

    def test_major_edit_preserves_shared_points_dimensions_and_detail_sizes(self):
        graph = {'nodes_mm': [[50, 50], [550, 50]], 'components': [
            {'id': 'd', 'kind': 'dimension', 'nodes': [0, 1], 'parameters': {'value_mm': 500}},
            {'id': 'w', 'kind': 'wall_face_pair', 'nodes': [0], 'parameters': {
                'thickness_mm': 80, 'face_extents_mm': [[150, 3781], [200, 3779]]}},
            {'id': 'o', 'kind': 'swing_opening', 'nodes': [1], 'parameters': {'radius_mm': 750}},
            {'id': 'r', 'kind': 'rectangular_loop', 'nodes': [0], 'parameters': {'width_mm': 3649, 'height_mm': 650}}]}
        before = copy.deepcopy(graph)
        result = snap_major_lengths(graph)
        self.assertEqual(graph, before)
        self.assertEqual(result['nodes_mm'], graph['nodes_mm'])
        self.assertEqual(result['components'][0], graph['components'][0])
        self.assertEqual(result['components'][2], graph['components'][2])
        self.assertEqual(result['components'][1]['parameters']['thickness_mm'], 80)
        self.assertEqual(result['components'][3]['parameters'], {'width_mm': 3600., 'height_mm': 650})
        for old, new in zip(graph['components'][1]['parameters']['face_extents_mm'], result['components'][1]['parameters']['face_extents_mm']):
            self.assertEqual(sum(old), sum(new))
            self.assertEqual(abs(new[1]-new[0]) % 100, 0)
        self.assertFalse(result['length_edit_receipt']['dimension_host_consistency_verified'])

    def test_invalid_checkpoint_fails_before_backbone_access(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'model.safetensors').write_bytes(b'invalid')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                load(directory, 'wrong-sha')


if __name__ == '__main__':
    unittest.main()
