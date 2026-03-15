# Grid Artifact Regression Report

- generated_at: `2026-03-15T16:39:20.683671+00:00`
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

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.1429, cur=0.1333, delta=-0.0096; avg_axis_margin_to_grid_threshold: prev=0.7571, cur=0.7667, delta=0.0096; avg_line_count: prev=28.0, cur=30.0, delta=2.0
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.75, cur=0.75, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.15, cur=0.15, delta=0.0; avg_line_count: prev=8.0, cur=8.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.1429, cur=0.1429, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.7571, cur=0.7571, delta=0.0; avg_line_count: prev=28.0, cur=28.0, delta=0.0

## Strategy diagnostics

- `consensus_qa`: avg_line_count=30.0, avg_axis_aligned_ratio=0.1333, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.7667, avg_axis_margin_score=76.67, max_axis_aligned_ratio=0.1333, max_axis_margin_to_grid_threshold=0.7667, p95_axis_aligned_ratio=0.1333, p95_axis_margin_to_grid_threshold=0.7667, min_axis_aligned_ratio=0.1333, min_axis_margin_to_grid_threshold=0.7667, avg_unique_x_count=47.0, avg_unique_y_count=46.0
- `hybrid_mvp`: avg_line_count=8.0, avg_axis_aligned_ratio=0.75, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.15, avg_axis_margin_score=15.0, max_axis_aligned_ratio=0.75, max_axis_margin_to_grid_threshold=0.15, p95_axis_aligned_ratio=0.75, p95_axis_margin_to_grid_threshold=0.15, min_axis_aligned_ratio=0.75, min_axis_margin_to_grid_threshold=0.15, avg_unique_x_count=3.0, avg_unique_y_count=3.0
- `two_stage_baseline`: avg_line_count=28.0, avg_axis_aligned_ratio=0.1429, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.7571, avg_axis_margin_score=75.71, max_axis_aligned_ratio=0.1429, max_axis_margin_to_grid_threshold=0.7571, p95_axis_aligned_ratio=0.1429, p95_axis_margin_to_grid_threshold=0.7571, min_axis_aligned_ratio=0.1429, min_axis_margin_to_grid_threshold=0.7571, avg_unique_x_count=43.0, avg_unique_y_count=42.0

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
