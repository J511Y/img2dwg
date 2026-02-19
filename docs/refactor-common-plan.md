# refactor/common 실행 계획

이 문서는 `refactor/common` 브랜치에서 아이디어 구현 비교를 위한 공통 뼈대를 정의한다.

## 목표
1. 이슈 검증용 테스트/벤치 파이프라인 구축
2. uv 의존성 정리
3. 구현 가이드 문서화
4. 에이전트 Linear 코멘트 표준화

## 전략 변경
기존의 "아이디어별 worktree 완전 분리" 대신, **전략 패턴 기반 단일 코드베이스 비교**를 기본으로 사용한다.

- 전략 인터페이스: `ConversionStrategy`
- 현재 비교 대상(초기):
  - `hybrid_mvp`
  - `two_stage_baseline`
  - `consensus_qa`
- 벤치 실행: `python scripts/benchmark_strategies.py --images <dir>`

## 공통 지표
- export_success_rate
- dxf_open_success_rate
- similarity score (geometry/text)
- ttfd / elapsed_ms
- manual_correction_time_sec

## 우선순위
- P0: 전략 인터페이스 + 벤치 러너 + 리포트 JSON
- P1: 유사도 측정 고도화, 실패 유형 분류 자동화
- P2: Human-in-the-loop 피드백 로그 반영
