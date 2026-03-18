# Grid Artifact Regression Report

- generated_at: `2026-03-18T08:10:53.434537+00:00`
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

- `consensus_qa`: avg_axis_aligned_ratio: prev=0.0315, cur=0.0315, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.8685, cur=0.8685, delta=0.0; avg_line_count: prev=128.0, cur=128.0, delta=0.0
- `hybrid_mvp`: avg_axis_aligned_ratio: prev=0.75, cur=0.75, delta=0.0; avg_axis_margin_to_grid_threshold: prev=0.15, cur=0.15, delta=0.0; avg_line_count: prev=8.0, cur=8.0, delta=0.0
- `two_stage_baseline`: avg_axis_aligned_ratio: prev=0.032, cur=0.0317, delta=-0.0003; avg_axis_margin_to_grid_threshold: prev=0.868, cur=0.8683, delta=0.0003; avg_line_count: prev=127.5, cur=128.8333, delta=1.3333

## Strategy diagnostics

- `consensus_qa`: avg_line_count=128.0, avg_axis_aligned_ratio=0.0315, std_axis_aligned_ratio=0.0026, avg_axis_margin_to_grid_threshold=0.8685, avg_axis_margin_score=86.85, max_axis_aligned_ratio=0.037, max_axis_margin_to_grid_threshold=0.863, p95_axis_aligned_ratio=0.037, p95_axis_margin_to_grid_threshold=0.863, min_axis_aligned_ratio=0.0267, min_axis_margin_to_grid_threshold=0.8733, avg_unique_x_count=243.0, avg_unique_y_count=243.0
- `hybrid_mvp`: avg_line_count=8.0, avg_axis_aligned_ratio=0.75, std_axis_aligned_ratio=0.0, avg_axis_margin_to_grid_threshold=0.15, avg_axis_margin_score=15.0, max_axis_aligned_ratio=0.75, max_axis_margin_to_grid_threshold=0.15, p95_axis_aligned_ratio=0.75, p95_axis_margin_to_grid_threshold=0.15, min_axis_aligned_ratio=0.75, min_axis_margin_to_grid_threshold=0.15, avg_unique_x_count=3.0, avg_unique_y_count=3.0
- `two_stage_baseline`: avg_line_count=128.8333, avg_axis_aligned_ratio=0.0317, std_axis_aligned_ratio=0.0049, avg_axis_margin_to_grid_threshold=0.8683, avg_axis_margin_score=86.83, max_axis_aligned_ratio=0.0444, max_axis_margin_to_grid_threshold=0.8556, p95_axis_aligned_ratio=0.0444, p95_axis_margin_to_grid_threshold=0.8556, min_axis_aligned_ratio=0.0247, min_axis_margin_to_grid_threshold=0.8753, avg_unique_x_count=244.6667, avg_unique_y_count=244.6667

## Top problematic samples

| strategy | case_id | image | flags | entities | unique_types | axis_ratio | unique_x | unique_y |
|---|---|---|---|---:|---:|---:|---:|---:|
