# Grid Artifact Regression Report

- generated_at: `2026-03-15T22:09:32.410659+00:00`
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

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.08, cur=0.0571, delta=-0.0229; avg_axis_margin_to_grid_threshold: prev=0.82, cur=0.8429, delta=0.0229; avg_line_count: prev=50.0, cur=70.0, delta=20.0
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.75, cur=0.75, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.15, cur=0.15, delta=0.0; avg_line_count: prev=8.0, cur=8.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.069, cur=0.069, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.831, cur=0.831, delta=0.0; avg_line_count: prev=58.0, cur=58.0, delta=0.0

## Strategy diagnostics

- `consensus_qa`: avg_line_count=70.0, avg_axis_aligned_ratio=0.0571, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.8429, avg_axis_margin_score=84.29, max_axis_aligned_ratio=0.0571, max_axis_margin_to_grid_threshold=0.8429, p95_axis_aligned_ratio=0.0571, p95_axis_margin_to_grid_threshold=0.8429, min_axis_aligned_ratio=0.0571, min_axis_margin_to_grid_threshold=0.8429, avg_unique_x_count=126.0, avg_unique_y_count=127.0
- `hybrid_mvp`: avg_line_count=8.0, avg_axis_aligned_ratio=0.75, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.15, avg_axis_margin_score=15.0, max_axis_aligned_ratio=0.75, max_axis_margin_to_grid_threshold=0.15, p95_axis_aligned_ratio=0.75, p95_axis_margin_to_grid_threshold=0.15, min_axis_aligned_ratio=0.75, min_axis_margin_to_grid_threshold=0.15, avg_unique_x_count=3.0, avg_unique_y_count=3.0
- `two_stage_baseline`: avg_line_count=58.0, avg_axis_aligned_ratio=0.069, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.831, avg_axis_margin_score=83.1, max_axis_aligned_ratio=0.069, max_axis_margin_to_grid_threshold=0.831, p95_axis_aligned_ratio=0.069, p95_axis_margin_to_grid_threshold=0.831, min_axis_aligned_ratio=0.069, min_axis_margin_to_grid_threshold=0.831, avg_unique_x_count=103.0, avg_unique_y_count=103.0

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
