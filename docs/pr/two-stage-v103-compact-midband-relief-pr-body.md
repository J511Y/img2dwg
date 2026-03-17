## Summary
- Reduce `two_stage_baseline` strategy bias on `web_floorplan_grid_v1` by adding a bounded compact mid-band relief term.
- Add a strategy-level regression test for the new compact low/mid-skew pocket.
- Refresh grid artifact regression reports and keep `failed_cases=0`.

## Linked Issues
- Closes #495
- Refs #494

## Validation Commands
- `UV_CACHE_DIR=.uv-cache uv run pytest -q tests/test_two_stage_v102_low_edge_midskew_relief.py tests/test_two_stage_v103_compact_midband_relief.py`
- `UV_CACHE_DIR=.uv-cache uv run ruff check src/img2dwg/strategies/two_stage.py tests/test_two_stage_v103_compact_midband_relief.py`
- `UV_CACHE_DIR=.uv-cache uv run ruff format --check src/img2dwg/strategies/two_stage.py tests/test_two_stage_v103_compact_midband_relief.py`
- `UV_CACHE_DIR=.uv-cache uv run mypy src/img2dwg/strategies/two_stage.py`
- `UV_CACHE_DIR=.uv-cache uv run python scripts/run_grid_artifact_regression.py --manifest eval/datasets/web_floorplan_grid_v1/manifest.csv --assets-dir output/web_floorplan_grid_v1 --benchmark-output output/benchmark/web_floorplan_grid_v1 --dataset-id web_floorplan_grid_v1 --git-ref "$(git rev-parse HEAD)" --skip-sync`

## Per-Strategy Before/After
| strategy | avg_axis_aligned_ratio | avg_axis_margin_to_grid_threshold | avg_unique_x_count | avg_unique_y_count | avg_line_count |
|---|---:|---:|---:|---:|---:|
| consensus_qa | 0.0365 -> 0.0365 | 0.8635 -> 0.8635 | 208.6667 -> 208.6667 | 208.6667 -> 208.6667 | 110.8333 -> 110.8333 |
| two_stage_baseline | 0.0364 -> 0.0358 | 0.8636 -> 0.8642 | 214.6667 -> 218.0 | 214.6667 -> 218.0 | 113.8333 -> 115.5 |
| hybrid_mvp | 0.75 -> 0.75 | 0.15 -> 0.15 | 3.0 -> 3.0 | 3.0 -> 3.0 | 8.0 -> 8.0 |

## Risk / Rollback
- The new relief is bounded to compact low/mid-skew, mid-complexity pockets so elongated corridor behavior stays unchanged.
- Roll back by removing the v103 compact mid-band relief block from `src/img2dwg/strategies/two_stage.py` and deleting `tests/test_two_stage_v103_compact_midband_relief.py`.
