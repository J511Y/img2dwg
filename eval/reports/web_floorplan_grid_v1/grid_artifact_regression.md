# Grid Artifact Regression Report

- generated_at: `2026-03-16T01:39:16.796493+00:00`
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

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.0428, cur=0.0428, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.8572, cur=0.8572, delta=0.0; avg_line_count: prev=93.8333, cur=93.8333, delta=0.0
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.75, cur=0.75, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.15, cur=0.15, delta=0.0; avg_line_count: prev=8.0, cur=8.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.054, cur=0.0501, delta=-0.0039; avg_axis_margin_to_grid_threshold: prev=0.846, cur=0.8499, delta=0.0039; avg_line_count: prev=74.1667, cur=80.1667, delta=6.0

## Strategy diagnostics

- `consensus_qa`: avg_line_count=93.8333, avg_axis_aligned_ratio=0.0428, std_axis_aligned_ratio=0.0026, avg_axis_margin_to_grid_threshold=0.8572, avg_axis_margin_score=85.72, max_axis_aligned_ratio=0.0488, max_axis_margin_to_grid_threshold=0.8512, p95_axis_aligned_ratio=0.0488, p95_axis_margin_to_grid_threshold=0.8512, min_axis_aligned_ratio=0.0392, min_axis_margin_to_grid_threshold=0.8608, avg_unique_x_count=174.6667, avg_unique_y_count=174.6667
- `hybrid_mvp`: avg_line_count=8.0, avg_axis_aligned_ratio=0.75, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.15, avg_axis_margin_score=15.0, max_axis_aligned_ratio=0.75, max_axis_margin_to_grid_threshold=0.15, p95_axis_aligned_ratio=0.75, p95_axis_margin_to_grid_threshold=0.15, min_axis_aligned_ratio=0.75, min_axis_margin_to_grid_threshold=0.15, avg_unique_x_count=3.0, avg_unique_y_count=3.0
- `two_stage_baseline`: avg_line_count=80.1667, avg_axis_aligned_ratio=0.0501, std_axis_aligned_ratio=0.0032, avg_axis_margin_to_grid_threshold=0.8499, avg_axis_margin_score=84.99, max_axis_aligned_ratio=0.0571, max_axis_margin_to_grid_threshold=0.8429, p95_axis_aligned_ratio=0.0571, p95_axis_margin_to_grid_threshold=0.8429, min_axis_aligned_ratio=0.0455, min_axis_margin_to_grid_threshold=0.8545, avg_unique_x_count=147.3333, avg_unique_y_count=147.3333

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
