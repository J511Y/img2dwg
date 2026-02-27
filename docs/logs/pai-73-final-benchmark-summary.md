# Benchmark Final Highlights

## Source Files
- summary: `output/benchmark/benchmark_summary.json`
- results: `output/benchmark/benchmark_results.json`

## Run Metadata
- dataset_id: `guardian-premerge`
- summary.git_ref: `00248f5065f77a212800e5079a5d5156d5ca775e`
- results.git_ref: `00248f5065f77a212800e5079a5d5156d5ca775e`

## Winner
- `hybrid_mvp` (rank=1, composite=0.7204)
- success_rate: 100.00%
- cad_loadable_rate: 100.00%
- mean_iou: 0.7888
- mean_topology_f1: 0.6869
- median_elapsed_ms: 99.63

## Triad Gate
- available: `True`
- passed: `True`

### Synthesis Deltas
- vs thesis(two_stage_baseline)
  - Δmean_iou: `0.0953`
  - Δmean_topology_f1: `0.1062`
  - Δmedian_elapsed_ms: `0.84`
- vs antithesis(consensus_qa)
  - Δmean_iou: `0.0512`
  - Δmean_topology_f1: `0.0562`
  - Δmedian_elapsed_ms: `-0.07`

## Ranking
| strategy | rank | composite | success | cad_loadable | mean_iou | topo_f1 | p95_ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| hybrid_mvp | 1 | 0.7204 | 100.00% | 100.00% | 0.7888 | 0.6869 | 148.14 |
| consensus_qa | 2 | 0.6936 | 100.00% | 100.00% | 0.7376 | 0.6307 | 123.11 |
| two_stage_baseline | 3 | 0.6701 | 100.00% | 100.00% | 0.6935 | 0.5807 | 152.98 |

## Output DXF Paths
- `consensus_qa`: `output/benchmark/consensus_qa`
- `hybrid_mvp`: `output/benchmark/hybrid_mvp`
- `two_stage_baseline`: `output/benchmark/two_stage_baseline`
