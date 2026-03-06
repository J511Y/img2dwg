"""Vision Encoder-Decoder 평가 지표."""

import json

from .utils import validate_json


def _validate_metric_inputs(predictions: list[str], references: list[str]) -> None:
    """입력 길이 일치 여부를 검증한다."""
    assert len(predictions) == len(references), "Predictions and references must have same length"


def compute_json_accuracy(predictions: list[str], references: list[str]) -> dict[str, float]:
    """
    JSON 파싱 정확도를 계산한다.

    Args:
        predictions: 예측 JSON 문자열 리스트
        references: 정답 JSON 문자열 리스트

    Returns:
        {
            "parse_success_rate": JSON 파싱 성공률,
            "exact_match": 완전 일치율,
        }

    Note:
        빈 입력(`len(predictions) == 0`)은 예외를 발생시키지 않고
        두 지표를 모두 0.0으로 반환한다.
    """
    _validate_metric_inputs(predictions, references)

    total = len(predictions)
    if total == 0:
        return {
            "parse_success_rate": 0.0,
            "exact_match": 0.0,
        }

    parse_success = 0
    exact_match = 0

    for pred, ref in zip(predictions, references, strict=False):
        # 파싱 성공 여부
        if validate_json(pred):
            parse_success += 1

            # 완전 일치 여부 (공백 무시)
            try:
                pred_obj = json.loads(pred)
                ref_obj = json.loads(ref)
                if pred_obj == ref_obj:
                    exact_match += 1
            except (json.JSONDecodeError, TypeError):
                continue

    return {
        "parse_success_rate": parse_success / total,
        "exact_match": exact_match / total,
    }


def compute_entity_accuracy(predictions: list[str], references: list[str]) -> dict[str, float]:
    """
    엔티티 수준 정확도를 계산한다.

    Args:
        predictions: 예측 JSON 문자열 리스트
        references: 정답 JSON 문자열 리스트

    Returns:
        {
            "entity_count_accuracy": 엔티티 개수 정확도,
            "entity_type_accuracy": 엔티티 타입 정확도,
        }
    """
    _validate_metric_inputs(predictions, references)

    entity_count_correct = 0
    entity_type_correct = 0
    total_entities_pred = 0
    total_entities_ref = 0

    for pred, ref in zip(predictions, references, strict=False):
        try:
            pred_obj = json.loads(pred)
            ref_obj = json.loads(ref)

            pred_entities = pred_obj.get("entities", [])
            ref_entities = ref_obj.get("entities", [])

            # 엔티티 개수
            if len(pred_entities) == len(ref_entities):
                entity_count_correct += 1

            # 엔티티 타입 비교
            pred_types = [e.get("type", e.get("t")) for e in pred_entities]
            ref_types = [e.get("type", e.get("t")) for e in ref_entities]

            # 순서 무시하고 타입 집합 비교
            if set(pred_types) == set(ref_types):
                entity_type_correct += 1

            total_entities_pred += len(pred_entities)
            total_entities_ref += len(ref_entities)

        except (json.JSONDecodeError, TypeError):
            continue

    total = len(predictions)

    return {
        "entity_count_accuracy": entity_count_correct / total if total > 0 else 0.0,
        "entity_type_accuracy": entity_type_correct / total if total > 0 else 0.0,
        "avg_entities_pred": total_entities_pred / total if total > 0 else 0.0,
        "avg_entities_ref": total_entities_ref / total if total > 0 else 0.0,
    }


def compute_metrics(predictions: list[str], references: list[str]) -> dict[str, float]:
    """
    모든 평가 지표를 계산한다.

    Args:
        predictions: 예측 JSON 문자열 리스트
        references: 정답 JSON 문자열 리스트

    Returns:
        평가 지표 딕셔너리

    Note:
        빈 입력은 평가 파이프라인의 안정성을 위해 모든 지표를 0.0으로 반환한다.
    """
    _validate_metric_inputs(predictions, references)

    if not predictions:
        return {
            "parse_success_rate": 0.0,
            "exact_match": 0.0,
            "entity_count_accuracy": 0.0,
            "entity_type_accuracy": 0.0,
            "avg_entities_pred": 0.0,
            "avg_entities_ref": 0.0,
        }

    json_metrics = compute_json_accuracy(predictions, references)
    entity_metrics = compute_entity_accuracy(predictions, references)

    return {
        **json_metrics,
        **entity_metrics,
    }
