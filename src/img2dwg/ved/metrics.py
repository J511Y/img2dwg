"""Vision Encoder-Decoder 평가 지표."""

import json
from typing import Dict, List

from .utils import validate_json


def compute_json_accuracy(predictions: List[str], references: List[str]) -> Dict[str, float]:
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
    """
    assert len(predictions) == len(references), "Predictions and references must have same length"
    
    parse_success = 0
    exact_match = 0
    
    for pred, ref in zip(predictions, references):
        # 파싱 성공 여부
        if validate_json(pred):
            parse_success += 1
            
            # 완전 일치 여부 (공백 무시)
            try:
                pred_obj = json.loads(pred)
                ref_obj = json.loads(ref)
                if pred_obj == ref_obj:
                    exact_match += 1
            except:
                pass
    
    total = len(predictions)
    
    return {
        "parse_success_rate": parse_success / total,
        "exact_match": exact_match / total,
    }


def compute_entity_accuracy(predictions: List[str], references: List[str]) -> Dict[str, float]:
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
    entity_count_correct = 0
    entity_type_correct = 0
    total_entities_pred = 0
    total_entities_ref = 0
    
    for pred, ref in zip(predictions, references):
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
            
        except:
            pass
    
    total = len(predictions)
    
    return {
        "entity_count_accuracy": entity_count_correct / total if total > 0 else 0.0,
        "entity_type_accuracy": entity_type_correct / total if total > 0 else 0.0,
        "avg_entities_pred": total_entities_pred / total if total > 0 else 0.0,
        "avg_entities_ref": total_entities_ref / total if total > 0 else 0.0,
    }


def compute_metrics(predictions: List[str], references: List[str]) -> Dict[str, float]:
    """
    모든 평가 지표를 계산한다.
    
    Args:
        predictions: 예측 JSON 문자열 리스트
        references: 정답 JSON 문자열 리스트
    
    Returns:
        평가 지표 딕셔너리
    """
    json_metrics = compute_json_accuracy(predictions, references)
    entity_metrics = compute_entity_accuracy(predictions, references)
    
    return {
        **json_metrics,
        **entity_metrics,
    }
