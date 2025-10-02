"""dwg_parser 모듈 테스트."""

from pathlib import Path
import pytest
import json

from img2dwg.data.dwg_parser import DWGParser


def test_dwg_parser_initialization():
    """DWGParser가 정상적으로 초기화되는지 테스트."""
    # Arrange & Act
    parser = DWGParser()
    
    # Assert
    assert parser is not None


def test_create_json_structure():
    """JSON 구조 생성이 정상 작동하는지 테스트."""
    # Arrange
    parser = DWGParser()
    dwg_path = Path("test_project/변경전후.dwg")
    entities = [
        {
            "type": "line",
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 100.0, "y": 100.0},
            "layer": "Wall",
        }
    ]
    
    # Act
    result = parser._create_json_structure(dwg_path, entities)
    
    # Assert
    assert "metadata" in result
    assert "entities" in result
    assert result["metadata"]["filename"] == "변경전후.dwg"
    assert result["metadata"]["type"] == "변경"
    assert result["metadata"]["entity_count"] == 1
    assert len(result["entities"]) == 1


def test_save_json(tmp_path):
    """JSON 저장이 정상 작동하는지 테스트."""
    # Arrange
    parser = DWGParser()
    data = {
        "metadata": {
            "filename": "test.dwg",
            "type": "변경",
            "entity_count": 1,
        },
        "entities": [
            {"type": "line", "start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 10}}
        ],
    }
    output_path = tmp_path / "test.json"
    
    # Act
    parser.save_json(data, output_path)
    
    # Assert
    assert output_path.exists()
    
    with open(output_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    
    assert loaded_data["metadata"]["filename"] == "test.dwg"
    assert len(loaded_data["entities"]) == 1


def test_parse_nonexistent_file_raises_error():
    """존재하지 않는 DWG 파일 파싱 시 에러를 발생시키는지 테스트."""
    # Arrange
    parser = DWGParser()
    nonexistent_path = Path("nonexistent_file.dwg")
    
    # Act & Assert
    with pytest.raises(FileNotFoundError):
        parser.parse(nonexistent_path)
