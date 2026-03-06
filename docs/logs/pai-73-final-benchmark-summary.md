# Benchmark Final Highlights

## Source Files
- summary: `output/benchmark/benchmark_summary.json`
- results: `output/benchmark/benchmark_results.json`

## Run Metadata
- dataset_id: `guardian-premerge`
- summary.git_ref: `81689b1`
- results.git_ref: `81689b1`

## Winner
- `hybrid_mvp` (rank=1, composite=0.7368)
- success_rate: 100.00%
- cad_loadable_rate: 100.00%
- mean_iou: 0.8328
- mean_topology_f1: 0.7077
- median_elapsed_ms: 86.97

## Triad Gate
- available: `True`
- passed: `True`

### Synthesis Deltas
- vs thesis(two_stage_baseline)
  - Δmean_iou: `0.0952`
  - Δmean_topology_f1: `0.1062`
  - Δmedian_elapsed_ms: `0.10`
- vs antithesis(consensus_qa)
  - Δmean_iou: `0.0512`
  - Δmean_topology_f1: `0.0562`
  - Δmedian_elapsed_ms: `-3.52`

## Ranking
| strategy | rank | composite | success | cad_loadable | mean_iou | topo_f1 | p95_ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| hybrid_mvp | 1 | 0.7368 | 100.00% | 100.00% | 0.8328 | 0.7077 | 98.78 |
| consensus_qa | 2 | 0.7099 | 100.00% | 100.00% | 0.7816 | 0.6515 | 101.58 |
| two_stage_baseline | 3 | 0.6865 | 100.00% | 100.00% | 0.7376 | 0.6015 | 98.37 |

## Output DXF Paths
- `consensus_qa`: `output/benchmark/consensus_qa`
- `hybrid_mvp`: `output/benchmark/hybrid_mvp`
- `two_stage_baseline`: `output/benchmark/two_stage_baseline`
