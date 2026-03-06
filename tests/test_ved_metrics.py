"""VED metrics regression tests."""

import pytest

from img2dwg.ved.metrics import compute_json_accuracy, compute_metrics


class TestVEDMetrics:
    def test_compute_json_accuracy_returns_zero_metrics_on_empty_input(self) -> None:
        result = compute_json_accuracy([], [])

        assert result == {
            "parse_success_rate": 0.0,
            "exact_match": 0.0,
        }

    def test_compute_metrics_returns_zeroed_metrics_on_empty_input(self) -> None:
        result = compute_metrics([], [])

        assert result == {
            "parse_success_rate": 0.0,
            "exact_match": 0.0,
            "entity_count_accuracy": 0.0,
            "entity_type_accuracy": 0.0,
            "avg_entities_pred": 0.0,
            "avg_entities_ref": 0.0,
        }

    @pytest.mark.parametrize(
        ("predictions", "references"),
        [
            (["{}"], []),
            ([], ["{}"]),
        ],
    )
    def test_length_mismatch_raises_assertion_error(
        self,
        predictions: list[str],
        references: list[str],
    ) -> None:
        with pytest.raises(AssertionError, match="same length"):
            compute_json_accuracy(predictions, references)

        with pytest.raises(AssertionError, match="same length"):
            compute_metrics(predictions, references)

    def test_compute_metrics_regression_for_normal_inputs(self) -> None:
        predictions = [
            '{"entities": [{"type": "LINE"}]}',
            '{"entities": [{"type": "CIRCLE"}]}',
        ]
        references = [
            '{"entities": [{"type": "LINE"}]}',
            '{"entities": [{"type": "ARC"}]}',
        ]

        result = compute_metrics(predictions, references)

        assert result["parse_success_rate"] == 1.0
        assert result["exact_match"] == 0.5
        assert result["entity_count_accuracy"] == 1.0
        assert result["entity_type_accuracy"] == 0.5
        assert result["avg_entities_pred"] == 1.0
        assert result["avg_entities_ref"] == 1.0
