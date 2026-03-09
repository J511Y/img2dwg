# Grid Artifact Regression Report

- generated_at: `2026-03-09T00:17:33.289188+00:00`
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

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.2727, cur=0.2727, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.6273, cur=0.6273, delta=0.0; avg_line_count: prev=22.0, cur=22.0, delta=0.0
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.4286, cur=0.4286, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.4714, cur=0.4714, delta=0.0; avg_line_count: prev=14.0, cur=14.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.3, cur=0.2727, delta=-0.0273; avg_axis_margin_to_grid_threshold: prev=0.6, cur=0.6273, delta=0.0273; avg_line_count: prev=20.0, cur=22.0, delta=2.0

## Strategy diagnostics

- `consensus_qa`: avg_line_count=22.0, avg_axis_aligned_ratio=0.2727, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.6273, avg_axis_margin_score=62.73, max_axis_aligned_ratio=0.2727, max_axis_margin_to_grid_threshold=0.6273, p95_axis_aligned_ratio=0.2727, p95_axis_margin_to_grid_threshold=0.6273, min_axis_aligned_ratio=0.2727, min_axis_margin_to_grid_threshold=0.6273, avg_unique_x_count=34.0, avg_unique_y_count=33.0
- `hybrid_mvp`: avg_line_count=14.0, avg_axis_aligned_ratio=0.4286, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.4714, avg_axis_margin_score=47.14, max_axis_aligned_ratio=0.4286, max_axis_margin_to_grid_threshold=0.4714, p95_axis_aligned_ratio=0.4286, p95_axis_margin_to_grid_threshold=0.4714, min_axis_aligned_ratio=0.4286, min_axis_margin_to_grid_threshold=0.4714, avg_unique_x_count=19.0, avg_unique_y_count=18.0
- `two_stage_baseline`: avg_line_count=22.0, avg_axis_aligned_ratio=0.2727, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.6273, avg_axis_margin_score=62.73, max_axis_aligned_ratio=0.2727, max_axis_margin_to_grid_threshold=0.6273, p95_axis_aligned_ratio=0.2727, p95_axis_margin_to_grid_threshold=0.6273, min_axis_aligned_ratio=0.2727, min_axis_margin_to_grid_threshold=0.6273, avg_unique_x_count=33.0, avg_unique_y_count=26.0

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
