# EXP-053 · 과잉 치수와 강제 제약으로 인한 도면 파괴의 분리·수정

상태: implemented / 동일 weight CPU10/10·252/252 / 연속 checkpoint 및fresh 검수 준비.
1,028개 본학습/holdout20/Space 배포는 하지 않는다. 기존 실패를 덮어쓰지 않는다.

## 확인된 원인

EXP-050 .0003 final 모델의 **후처리 전** 신규5 구조F1은 .996400~1.0이고component/
shared-reference도 거의 재현됐다. 실제140개 치수를 post-forward GT correspondence로
검사하니 숫자/종류/각도 오류0, raw label-geometry residual 최대1.6934mm였다.
그러나3개 사례에는GT에없는DIMENSION이4/2/3개 더 나왔다. 이9개 query의미정parameter를
강제치수로 투입하면서project가노드를최대3815/2332/1889mm 이동시켰다.
몇개과잉 객체가 거의맞는전체구조를무너뜨린것이다. source decoder는이미학습된image
count를무시하고no-object .5 threshold만사용했고검증없이모든치수를hard equation으로썼다.

이는현재10개 실험에서확인한별도실패원인이다. EXP-047에서확인한1,028모델의첫Adam
update/raw좌표불안정을모두이문제로설명하지않는다. low loss/평균node오차만보고추가
decoder 용량 가설로진행한것은판단미흡이었다. 기존before_constraints와추가DIMcount를
먼저봤어야했다. EXP-052를cancelled-diagnostic-pivot으로중단하고partial결과를보존했다.
해당비선형구조의유용성전체를기각하거나실행성공으로바꾸지않는다.

## 변경 · source CAD/GT 없이

- 모델log_count의image-predicted count로전체reserve에서node active logit/foreground-vs-
  no-object log odds의상위query를선택한다. query prefix나GT count로자르지않는다.
  log odds는probability1로포화된query도구별한다. reserve가부족하면완성을거부한다.
- numeric label과예측참조의실제길이가10mm 안에서일치하는dimension만유효후보로
  인정한다. nonpositive/불일치후보는최종CAD에서제외하고값·길이·잔차·query를기록한다.
  이후count ranking을다시해정상객체를가짜치수때문에빼지않는다.
- 집합제약보정이10mm 이상노드를움직이면적용하지않고rejected로돌려준다.
  confidence로이기하실패를통과시키지않는다.10mm는기존동결구조허용오차를쓴다.

이검사는CAD/정답/의뢰ID를읽지않는다. real DIM252개 모두유지했는지는**별도검증**한다.
새입력에서제외된candidate가실제필요치수일수있으므로후속HITL에서명시적으로검수한다.
원모델및기존Space 기본동작은수정하지않았고이번로컬실험의decoder contract로실행한다.

## 동일 source weight의요인 분리

source .0003 final SHA `79a05c986e28c09e9875f6501339c052a869ebe0fd705459fce18692e1a8ae9b`,
source Adam/assignment 누적9052epoch. same10/train/native protocol을유지했다.

| 추론/제약 변경만 | 기존5 | 신규5 | 전체필수DIM |
| --- | --- | --- | ---: |
| 기존no-object + 무제한project | 5/5 | 2/5 | 201/252 |
| image-count ranked set만 | 5/5 | 3/5 | 209/252 |
| dimension consistency + project trust region | 5/5 | 5/5 | 252/252 |
| ranked set + dimension consistency | 5/5 | 5/5 | 252/252 |

결합조건 신규F1 .998430813/component .998670818/ref .998260535,
기존F1 .999284692/component .999003113/ref .999643161다.
correct numeric/geometry252·missing0·extra0이며최대보정이동1.15023mm다.
다른 .0001 final weight의fresh image추론은9/10·251/252여서통과모델로채택하지않는다.
따라서decoder수정만으로모든checkpoint가자동통과한다고주장하지않는다.

## 실제 안정성·직접 검수 완료조건

같은.0003 source의모델/Adam/assignment를복원하고LR1e-6에서TRAIN10 내새5만
짧게이어간다. 이전과같은1/8 초기quality검사에서두개의연속checkpoint10/10·252/252·
nativeDXF가통과하면멈춘다. 조건5분/suite8분/job20분상한은수렴기준이아니다.
새source weight와decoder contract를따로고정하여fresh DINO IMAGE→MODEL→CAD를검사하고
직접10개비교/모델DXF→DWG→DXF를확인한다. 실제CAD UI edit/save는별도상태로남긴다.
이는10개train 재현이며 일반화/1,028학습/Space 배포 성공을뜻하지않는다.
