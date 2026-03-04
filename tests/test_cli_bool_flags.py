"""CLI boolean flag 동작 검증 테스트."""

from scripts.convert_dwg import parse_args as parse_convert_args
from scripts.generate_dataset import parse_args as parse_dataset_args


def test_convert_dwg_boolean_optional_flags() -> None:
    """convert_dwg는 --flag/--no-flag 양방향 제어를 지원해야 한다."""
    default_args = parse_convert_args([])
    assert default_args.optimize is True
    assert default_args.layout_analysis is False
    assert default_args.compact_schema is False

    toggled_args = parse_convert_args(
        [
            "--no-optimize",
            "--layout-analysis",
            "--compact-schema",
        ]
    )
    assert toggled_args.optimize is False
    assert toggled_args.layout_analysis is True
    assert toggled_args.compact_schema is True


def test_generate_dataset_boolean_optional_flags() -> None:
    """generate_dataset는 네트워크 옵션 기본 비활성 + 명시적 활성화를 지원해야 한다."""
    default_args = parse_dataset_args([])
    assert default_args.enable_tiling is True
    assert default_args.compact_schema is False
    assert default_args.optimize is True
    assert default_args.use_image_url is False

    toggled_args = parse_dataset_args(
        [
            "--no-enable-tiling",
            "--compact-schema",
            "--no-optimize",
            "--use-image-url",
            "--image-service",
            "imgur",
        ]
    )
    assert toggled_args.enable_tiling is False
    assert toggled_args.compact_schema is True
    assert toggled_args.optimize is False
    assert toggled_args.use_image_url is True
    assert toggled_args.image_service == "imgur"
