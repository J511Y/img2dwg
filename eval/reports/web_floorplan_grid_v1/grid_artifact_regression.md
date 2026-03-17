# Grid Artifact Regression Report

- generated_at: `2026-03-17T11:41:25.196434+00:00`
- total_cases: `36`
- passed_cases: `36`
- failed_cases: `0`
- pass_rate: `1.0`

## Failure reasons

- none

## Delta vs previous

- `failed_cases`: previous=0, current=0, delta=0
- `pass_rate`: previous=1.0, current=1.0, delta=0.0
- `suspicious_grid_pattern`: previous=0, current=0, delta=0
- `low_entity_count`: previous=0, current=0, delta=0
- `low_entity_diversity`: previous=0, current=0, delta=0
- `hybrid_avg_axis_margin_score`: previous=15.0, current=15.0, delta=0.0
- `hybrid_avg_axis_aligned_ratio`: previous=0.75, current=0.75, delta=0.0
- `hybrid_avg_axis_margin_to_grid_threshold`: previous=0.15, current=0.15, delta=0.0
- `hybrid_avg_unique_x_count`: previous=3.0, current=3.0, delta=0.0
- `hybrid_avg_unique_y_count`: previous=3.0, current=3.0, delta=0.0
- `hybrid_avg_line_count`: previous=8.0, current=8.0, delta=0.0
- `hybrid_std_axis_aligned_ratio`: previous=0.0, current=0.0, delta=0.0
- `hybrid_max_axis_margin_to_grid_threshold`: previous=0.15, current=0.15, delta=0.0
- `hybrid_max_axis_aligned_ratio`: previous=0.75, current=0.75, delta=0.0
- `hybrid_p95_axis_margin_to_grid_threshold`: previous=0.15, current=0.15, delta=0.0
- `hybrid_p95_axis_aligned_ratio`: previous=0.75, current=0.75, delta=0.0
- `hybrid_min_axis_margin_to_grid_threshold`: previous=0.15, current=0.15, delta=0.0
- `hybrid_min_axis_aligned_ratio`: previous=0.75, current=0.75, delta=0.0

## Strategy delta vs previous

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.0341, cur=0.0341, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.8659, cur=0.8659, delta=0.0; avg_line_count: prev=118.5, cur=118.5, delta=0.0
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.75, cur=0.75, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.15, cur=0.15, delta=0.0; avg_line_count: prev=8.0, cur=8.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.0344, cur=0.0339, delta=-0.0005; avg_axis_margin_to_grid_threshold: prev=0.8656, cur=0.8661, delta=0.0005; avg_line_count: prev=119.3333, cur=121.3333, delta=2.0

## Strategy diagnostics

- `consensus_qa`: avg_line_count=118.5, avg_axis_aligned_ratio=0.0341, std_axis_aligned_ratio=0.0031, avg_axis_margin_to_grid_threshold=0.8659, avg_axis_margin_score=86.59, max_axis_aligned_ratio=0.04, max_axis_margin_to_grid_threshold=0.86, p95_axis_aligned_ratio=0.04, p95_axis_margin_to_grid_threshold=0.86, min_axis_aligned_ratio=0.0282, min_axis_margin_to_grid_threshold=0.8718, avg_unique_x_count=224.0, avg_unique_y_count=224.0
- `hybrid_mvp`: avg_line_count=8.0, avg_axis_aligned_ratio=0.75, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.15, avg_axis_margin_score=15.0, max_axis_aligned_ratio=0.75, max_axis_margin_to_grid_threshold=0.15, p95_axis_aligned_ratio=0.75, p95_axis_margin_to_grid_threshold=0.15, min_axis_aligned_ratio=0.75, min_axis_margin_to_grid_threshold=0.15, avg_unique_x_count=3.0, avg_unique_y_count=3.0
- `two_stage_baseline`: avg_line_count=121.3333, avg_axis_aligned_ratio=0.0339, std_axis_aligned_ratio=0.0058, avg_axis_margin_to_grid_threshold=0.8661, avg_axis_margin_score=86.61, max_axis_aligned_ratio=0.0476, max_axis_margin_to_grid_threshold=0.8524, p95_axis_aligned_ratio=0.0476, p95_axis_margin_to_grid_threshold=0.8524, min_axis_aligned_ratio=0.0253, min_axis_margin_to_grid_threshold=0.8747, avg_unique_x_count=229.5, avg_unique_y_count=229.6667

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
