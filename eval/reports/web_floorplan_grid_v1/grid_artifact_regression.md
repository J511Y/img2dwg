# Grid Artifact Regression Report

- generated_at: `2026-03-16T00:09:47.707412+00:00`
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

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.0507, cur=0.0479, delta=-0.0028; avg_axis_margin_to_grid_threshold: prev=0.8493, cur=0.852, delta=0.0027; avg_line_count: prev=79.0, cur=83.5, delta=4.5
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.75, cur=0.75, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.15, cur=0.15, delta=0.0; avg_line_count: prev=8.0, cur=8.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.0575, cur=0.054, delta=-0.0035; avg_axis_margin_to_grid_threshold: prev=0.8425, cur=0.846, delta=0.0035; avg_line_count: prev=69.6667, cur=74.1667, delta=4.5

## Strategy diagnostics

- `consensus_qa`: avg_line_count=83.5, avg_axis_aligned_ratio=0.0479, std_axis_aligned_ratio=0.0014, avg_axis_margin_to_grid_threshold=0.852, avg_axis_margin_score=85.2, max_axis_aligned_ratio=0.05, max_axis_margin_to_grid_threshold=0.85, p95_axis_aligned_ratio=0.05, p95_axis_margin_to_grid_threshold=0.85, min_axis_aligned_ratio=0.0455, min_axis_margin_to_grid_threshold=0.8545, avg_unique_x_count=154.0, avg_unique_y_count=154.0
- `hybrid_mvp`: avg_line_count=8.0, avg_axis_aligned_ratio=0.75, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.15, avg_axis_margin_score=15.0, max_axis_aligned_ratio=0.75, max_axis_margin_to_grid_threshold=0.15, p95_axis_aligned_ratio=0.75, p95_axis_margin_to_grid_threshold=0.15, min_axis_aligned_ratio=0.75, min_axis_margin_to_grid_threshold=0.15, avg_unique_x_count=3.0, avg_unique_y_count=3.0
- `two_stage_baseline`: avg_line_count=74.1667, avg_axis_aligned_ratio=0.054, std_axis_aligned_ratio=0.0022, avg_axis_margin_to_grid_threshold=0.846, avg_axis_margin_score=84.6, max_axis_aligned_ratio=0.0571, max_axis_margin_to_grid_threshold=0.8429, p95_axis_aligned_ratio=0.0571, p95_axis_margin_to_grid_threshold=0.8429, min_axis_aligned_ratio=0.05, min_axis_margin_to_grid_threshold=0.85, avg_unique_x_count=135.3333, avg_unique_y_count=135.3333

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
