import sys
import tempfile
import unittest
from pathlib import Path

import ezdxf
import torch
from img2dwg.cad import extract
from img2dwg.raw_model import CanonicalDecoder, encode_target, raw_loss
from img2dwg.raw_evaluation import evaluate_case, measurement
from img2dwg.dimension_solver import constrain_dimensions


def graph(length=1000, value=1000):
    return {'schema': 'img2dwg-vector/v1', 'canvas': [2000, 2000], 'scale': 1., 'units': 'mm',
            'components': [{'kind': 'segment', 'points': [[100, 100], [1100, 100], [600, 100]], 'role': 0},
                           {'kind': 'dimension', 'points': [[100, 100], [100 + length, 100], [600, 50]],
                            'dimension_kind': 0, 'angle_cad': 0., 'measurement_mm': value,
                            'predicted_value_mm': value, 'value_text': str(value), 'role': 0}]}


class RawPairTests(unittest.TestCase):
    def test_small_native_dimension_is_not_dropped(self):
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / 'small.dxf'
            doc = ezdxf.new('R2018'); doc.units = 4
            d = doc.modelspace().add_linear_dim(base=(0, 500), p1=(0, 0), p2=(5, 0))
            d.render(); doc.saveas(p)
            target = extract(p, [-100, -100, 20000, 20000], 512, min_length_pixels=0)
            self.assertEqual(sum(c['kind'] == 'dimension' for c in target['components']), 1)

    def test_numeric_label_does_not_hide_wrong_geometry(self):
        true = graph(); wrong = graph(1300, 1000)
        result = evaluate_case(wrong, true, {'audit_errors': 0})
        self.assertFalse(result['passed'])
        self.assertEqual(result['components']['dimension']['correct_geometry_and_value'], 0)
        self.assertEqual(measurement(wrong['components'][1], wrong), 1300)

    def test_complete_numeric_fixture_passes_only_baseline(self):
        true = graph(); result = evaluate_case(true, true, {'audit_errors': 0})
        self.assertTrue(result['passed'])
        self.assertFalse(result['complete_DWG_product_passed'])

    def test_capacity_cannot_hide_missing_training_targets(self):
        with self.assertRaisesRegex(ValueError, 'capacity'):
            encode_target(graph(), 1, 64)

    def test_encoder_features_receive_finite_decoder_gradient(self):
        model = CanonicalDecoder(8, hidden=24)
        pred = model(torch.randn(1, 16, 768))
        target = encode_target(graph(), 8, 64)
        loss, _ = raw_loss(pred, [target]); loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in model.parameters() if p.grad is not None), 0)
        changed = model(torch.zeros(1, 16, 768))
        self.assertFalse(torch.allclose(pred['geometry'], changed['geometry']))

    def test_dimension_solver_changes_attached_line_geometry(self):
        example = graph(1300, 1000)
        example['geometry_source'] = 'trained-raw-test-fixture'
        example['components'][0]['points'][1][0] = 1400
        solved = constrain_dimensions(example)
        self.assertAlmostEqual(measurement(solved['components'][1], solved), 1000, places=5)
        self.assertAlmostEqual(solved['components'][0]['points'][1][0] - solved['components'][0]['points'][0][0], 1000, places=5)
        self.assertEqual(example['components'][0]['points'][1][0], 1400)
        self.assertFalse(solved['dimension_solver']['target_access'])


if __name__ == '__main__':
    unittest.main()
