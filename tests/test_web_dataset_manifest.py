from __future__ import annotations

import csv
from pathlib import Path

MANIFEST_PATH = Path("eval/datasets/web_image2cad_v1/manifest.csv")

REQUIRED_COLUMNS = {
    "case_id",
    "image_filename",
    "image_url",
    "image_sha256",
    "dxf_candidate_filename",
    "dxf_candidate_url",
    "dxf_candidate_sha256",
    "source_repository",
    "source_commit",
    "license_spdx",
    "license_url",
    "pairing_type",
    "notes",
}


def test_web_dataset_manifest_has_required_columns_and_rows() -> None:
    assert MANIFEST_PATH.exists(), "dataset manifest must exist"

    with MANIFEST_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert REQUIRED_COLUMNS.issubset(set(reader.fieldnames))

        rows = list(reader)

    assert len(rows) >= 3, "dataset manifest should include at least 3 benchmark rows"

    case_ids = [row["case_id"] for row in rows]
    assert len(case_ids) == len(set(case_ids)), "case_id must be unique"

    for row in rows:
        assert row["source_repository"].startswith("https://")
        assert row["license_spdx"].strip()
        assert row["license_url"].startswith("https://")
        assert len(row["image_sha256"].strip()) == 64
        assert len(row["dxf_candidate_sha256"].strip()) == 64
