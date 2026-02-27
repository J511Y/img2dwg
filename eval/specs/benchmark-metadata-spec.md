# Benchmark Metadata Spec

`eval_summary*.json` 산출물에는 아래 블록을 포함해야 한다.

```json
{
  "benchmark_metadata": {
    "git_ref": "<40-hex-sha>",
    "generated_at": "<YYYY-MM-DDTHH:mm:ssZ>",
    "dataset_manifest_ref": "<repo-relative-path>"
  }
}
```

## Validation Rules
- `git_ref`: 정규식 `^[0-9a-f]{40}$`
- `generated_at`: UTC 고정 포맷 `YYYY-MM-DDTHH:mm:ssZ`
- `dataset_manifest_ref`: 절대경로 금지, `..` 세그먼트 금지, 빈 문자열 금지

## Notes
- triad/benchmark 파생 아티팩트도 동일 블록을 유지한다.
- `scripts/export_triad_artifacts.py` 경로에서는 `--require-triad` 유무와 무관하게 위 규칙 위반 시 즉시 실패(fail fast)해야 한다.
- 자동 검증은 `scripts/export_triad_artifacts.py --require-triad` 실행과 `tests/test_export_triad_artifacts.py`로 커버한다.
