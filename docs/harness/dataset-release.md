# 사내 페어 데이터셋 확장·비공개 버킷 릴리스

2026-10-13 사용자 확정 정책: 같은 워크 의뢰 연결 폴더의 `준공도면`과 `변경전후.dwg`는 같은 현장의 input/output이다. 이 관계는 수집 정답 근거로 받아들이며 별도 이미지 구조 정합·사람 페어 승인을 요구하지 않는다. CAD의 변경전 추출·컴포넌트 전처리·파일 무결성은 데이터 처리 검사다. 모델 confidence로 이 사용자 확정 페어 관계를 다시 판정하지 않는다.

## 수집과 보존

- 운영 워크 연결 인덱스의 immediate children만 발견한다. 준공도면 stem과 변경전후.dwg 이름은 정확히 일치해야 한다.
- 원본 이미지/DWG는 읽기 전용이며 새 run 폴더에 복사한다. source/copy SHA-256, 원본 size/mtime 전후를 검사한다.
- 최소 1,000개는 서로 다른 exact image+DWG content pair로 구성한다. augment 수·native entity 수를 의뢰 페어 수로 세지 않는다.
- 다중 reference는 원본을 모두 보관하며 decode 가능한 raster 중 최대 pixel-area reference를 primary로 선택하고 선택 근거/EXIF를 기록한다. primary 자동 선택은 동일 폴더 페어 근거를 바꾸지 않는다.
- native BLOCK/INSERT·DIMENSION·styles·raw geometry와 tag를 유지한다. layer/type partition을 문·벽·공간의 확정 객체로 승격하지 않는다.
- 자동 before crop이 불확실하거나 파일/치수 무결성 검사에 실패한 건은 처리 사유와 원본 페어를 보존한다. 이는 현장 페어 부정 판정이 아니다.

## 단계별 실행

```powershell
.\.venv\Scripts\python.exe scripts/discover_pilot.py --index <private-work-index> --output <new-run>/discovery --wanted 1400 --max-folders 8764
.\.venv\Scripts\python.exe scripts/prepare_dataset.py collect --discovery <new-run>/discovery/discovery.json --root <new-run> --workers 4
.\.venv\Scripts\python.exe scripts/prepare_dataset.py convert --root <new-run> --input <new-run>/raw_dwgs --output <new-run>/source_dxfs --converter <ODA-executable> --format DXF --pattern '*.dwg'
.\.venv\Scripts\python.exe scripts/prepare_dataset.py preprocess --root <new-run> --source-module <crop-module> --workers 4
.\.venv\Scripts\python.exe scripts/package_dataset.py --root <new-run> --minimum 1000 --shard-size 64
hf buckets sync <new-run>/bundle hf://buckets/<private-bucket>/datasets/<immutable-version> --plan <private-sync-plan.jsonl>
hf buckets sync --apply <private-sync-plan.jsonl>
.\.venv\Scripts\python.exe scripts/verify_bucket_dataset.py --prefix hf://buckets/<private-bucket>/datasets/<immutable-version> --output <private-readback> --minimum 1000
```

ODA는 로컬 사본으로만 배치 실행하며 Windows GUI를 숨긴다. worker는 receipt 및 코드/dependency hash가 맞는 산출물만 resume한다. 단계 중간 실행을 최종 성공으로 표시하지 않는다. 이미 업로드한 버전은 새 파이프라인으로 덮어쓰지 않고 다음 버전을 만든다. sync에 delete 옵션을 넣지 않는다.

## 릴리스 형식

`records.jsonl`은 sample ID, primary image/CAD/native component path/hash, shard, 단위, before bbox, 치수 보존 결과, split/group ID를 가진다. `provenance.jsonl`은 파일 hash/size/mtime와 원본 무변경을 기록하며 실제 공유 경로·고객/의뢰번호는 클라우드 metadata에서 제거한다. 원본 도면 내용 자체는 비공개 버킷의 허용된 데이터다.

각 tar.gz shard에는 다음이 들어간다.

```text
P<case-hash>/source.dwg
P<case-hash>/input/reference-*.jpg|png|tif|...
P<case-hash>/input-preview.jpg
P<case-hash>/before.dxf
P<case-hash>/native-components.json.gz
```

원본 input은 preview가 아니라 full-resolution reference다. EXIF orientation을 적용해 로딩한다. native component JSON은 root entities, native dimension/block/text/mline, 모든 보관 block definition·style·DIMASSOC raw tag와 미해석 geometry partition을 기록한다. DIMENSION 그림의 선·문자는 독립 치수 정답으로 중복 집계하지 않는다. semantic assembly catalog와 DIMASSOC endpoint 검증은 후속 전처리 상태를 명시한다.

## 중복·split·학습 경계

같은 image hash, DWG hash 또는 translation/회전/반전 동등 LINE geometry fingerprint를 union group으로 묶어 deterministic train/validation/calibration/test에 배정한다. exact identity cross-split 누수 0을 검사한다. geometry fingerprint는 완전한 평면 계열 분류기가 아니며 near layout family grouping 완료를 주장하지 않는다. 이 split은 준비용이며 모델 밀봉 평가 전에 near-family/과거 학습 노출을 추가 검토한다.

raw/native component 준비를 모델 학습·의미 라벨 검수·실물 치수 정확도 또는 CAD 사용자 편집 성공으로 승격하지 않는다. 단위 불명·표시 치수 충돌·미지원 객체는 실제 값/상태를 보존한다. 실물 geometry 제약은 다음 모델/solver 단계에서 검사한다.

## 검증

release가 최소 1,000개인지, exact pair duplicate/known identity cross-split leak가 없는지 검사한다. 원본 복사와 crop에서 치수 측정점·값·effective style이 유지되는지 확인한다. DXF save가 생략된 style default를 명시하는 경우는 동등 값으로 정규화하되 실제 배율/치수 변화는 실패 처리한다.

업로드 후 metadata를 다시 읽고 **모든 remote shard를 다운로드**해 SHA-256/bytes를 대조한다. archive 안의 각 primary 이미지·원본 DWG·변경전 DXF·native component 파일 해시와 case membership도 확인한다. private receipt에는 remote readback과 검사 한계를 기록한다.

현재 완료 버전은 [2026-10-13 v0.2](../research/2026-10-13-dataset-v02-release.md)다. 메모리 누적을 막기 위해 100개 단위 process pool을 교체한다. 검증된 동등 성능 최적화 전의 receipt를 재사용할 때만 명시적 `--reuse-protocol <sha256>`를 쓰며 원본/산출물 해시와 실제 동일 crop/entity/치수/fingerprint 비교를 근거로 남긴다. schema/의미 변경에 이 예외를 사용하지 않는다.
