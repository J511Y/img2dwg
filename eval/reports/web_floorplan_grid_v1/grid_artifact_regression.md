# Grid Artifact Regression Report

- generated_at: `2026-03-09T02:49:09.859977+00:00`
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
- `hybrid_avg_axis_margin_score`: previous=47.14, current=47.14, delta=0.0
- `hybrid_avg_axis_aligned_ratio`: previous=0.4286, current=0.4286, delta=0.0
- `hybrid_avg_axis_margin_to_grid_threshold`: previous=0.4714, current=0.4714, delta=0.0
- `hybrid_avg_unique_x_count`: previous=19.0, current=19.0, delta=0.0
- `hybrid_avg_unique_y_count`: previous=18.0, current=18.0, delta=0.0
- `hybrid_avg_line_count`: previous=14.0, current=14.0, delta=0.0
- `hybrid_std_axis_aligned_ratio`: previous=0.0, current=0.0, delta=0.0
- `hybrid_max_axis_margin_to_grid_threshold`: previous=0.4714, current=0.4714, delta=0.0
- `hybrid_max_axis_aligned_ratio`: previous=0.4286, current=0.4286, delta=0.0
- `hybrid_p95_axis_margin_to_grid_threshold`: previous=0.4714, current=0.4714, delta=0.0
- `hybrid_p95_axis_aligned_ratio`: previous=0.4286, current=0.4286, delta=0.0
- `hybrid_min_axis_margin_to_grid_threshold`: previous=0.4714, current=0.4714, delta=0.0
- `hybrid_min_axis_aligned_ratio`: previous=0.4286, current=0.4286, delta=0.0

## Strategy delta vs previous

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.2308, cur=0.2143, delta=-0.0165; avg_axis_margin_to_grid_threshold: prev=0.6692, cur=0.6857, delta=0.0165; avg_line_count: prev=26.0, cur=28.0, delta=2.0
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.4286, cur=0.4286, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.4714, cur=0.4714, delta=0.0; avg_line_count: prev=14.0, cur=14.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.2308, cur=0.2308, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.6692, cur=0.6692, delta=0.0; avg_line_count: prev=26.0, cur=26.0, delta=0.0

## Strategy diagnostics

- `consensus_qa`: avg_line_count=28.0, avg_axis_aligned_ratio=0.2143, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.6857, avg_axis_margin_score=68.57, max_axis_aligned_ratio=0.2143, max_axis_margin_to_grid_threshold=0.6857, p95_axis_aligned_ratio=0.2143, p95_axis_margin_to_grid_threshold=0.6857, min_axis_aligned_ratio=0.2143, min_axis_margin_to_grid_threshold=0.6857, avg_unique_x_count=43.0, avg_unique_y_count=41.0
- `hybrid_mvp`: avg_line_count=14.0, avg_axis_aligned_ratio=0.4286, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.4714, avg_axis_margin_score=47.14, max_axis_aligned_ratio=0.4286, max_axis_margin_to_grid_threshold=0.4714, p95_axis_aligned_ratio=0.4286, p95_axis_margin_to_grid_threshold=0.4714, min_axis_aligned_ratio=0.4286, min_axis_margin_to_grid_threshold=0.4714, avg_unique_x_count=19.0, avg_unique_y_count=18.0
- `two_stage_baseline`: avg_line_count=26.0, avg_axis_aligned_ratio=0.2308, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.6692, avg_axis_margin_score=66.92, max_axis_aligned_ratio=0.2308, max_axis_margin_to_grid_threshold=0.6692, p95_axis_aligned_ratio=0.2308, p95_axis_margin_to_grid_threshold=0.6692, min_axis_aligned_ratio=0.2308, min_axis_margin_to_grid_threshold=0.6692, avg_unique_x_count=41.0, avg_unique_y_count=34.0

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
