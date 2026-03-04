import csv
from pathlib import Path


def test_web_dataset_manifest_includes_jpg_png_and_license_metadata() -> None:
    manifest = (
        Path(__file__).resolve().parent.parent
        / "eval"
        / "datasets"
        / "web_image2cad_v1"
        / "manifest.csv"
    )

    assert manifest.exists()

    with manifest.open("r", encoding="utf-8", newline="") as fp:
        rows = list(csv.DictReader(fp))

    assert rows

    image_filenames = {row["image_filename"].lower() for row in rows}
    assert any(name.endswith(".jpg") or name.endswith(".jpeg") for name in image_filenames)
    assert any(name.endswith(".png") for name in image_filenames)

    for row in rows:
        assert row["dxf_candidate_url"].startswith("https://")
        assert row["dxf_candidate_filename"].lower().endswith(".dxf")
        assert row["license_spdx"].strip()
        assert row["license_url"].startswith("https://")
        assert row["source_repository"].startswith("https://github.com/")
