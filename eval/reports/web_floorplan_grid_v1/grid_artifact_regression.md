# Grid Artifact Regression Report

- generated_at: `2026-03-15T18:39:24.991253+00:00`
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

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.1176, cur=0.1176, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.7824, cur=0.7824, delta=0.0; avg_line_count: prev=34.0, cur=34.0, delta=0.0
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.75, cur=0.75, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.15, cur=0.15, delta=0.0; avg_line_count: prev=8.0, cur=8.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.1333, cur=0.1176, delta=-0.0157; avg_axis_margin_to_grid_threshold: prev=0.7667, cur=0.7824, delta=0.0157; avg_line_count: prev=30.0, cur=34.0, delta=4.0

## Strategy diagnostics

- `consensus_qa`: avg_line_count=34.0, avg_axis_aligned_ratio=0.1176, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.7824, avg_axis_margin_score=78.24, max_axis_aligned_ratio=0.1176, max_axis_margin_to_grid_threshold=0.7824, p95_axis_aligned_ratio=0.1176, p95_axis_margin_to_grid_threshold=0.7824, min_axis_aligned_ratio=0.1176, min_axis_margin_to_grid_threshold=0.7824, avg_unique_x_count=54.0, avg_unique_y_count=55.0
- `hybrid_mvp`: avg_line_count=8.0, avg_axis_aligned_ratio=0.75, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.15, avg_axis_margin_score=15.0, max_axis_aligned_ratio=0.75, max_axis_margin_to_grid_threshold=0.15, p95_axis_aligned_ratio=0.75, p95_axis_margin_to_grid_threshold=0.15, min_axis_aligned_ratio=0.75, min_axis_margin_to_grid_threshold=0.15, avg_unique_x_count=3.0, avg_unique_y_count=3.0
- `two_stage_baseline`: avg_line_count=34.0, avg_axis_aligned_ratio=0.1176, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.7824, avg_axis_margin_score=78.24, max_axis_aligned_ratio=0.1176, max_axis_margin_to_grid_threshold=0.7824, p95_axis_aligned_ratio=0.1176, p95_axis_margin_to_grid_threshold=0.7824, min_axis_aligned_ratio=0.1176, min_axis_margin_to_grid_threshold=0.7824, avg_unique_x_count=55.0, avg_unique_y_count=54.0

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
