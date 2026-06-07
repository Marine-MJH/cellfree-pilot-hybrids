# Presentation Reference Report

작성일: 2026-06-07

이 문서는 발표 준비 과정에서 논의한 해석, 실험 결과, 말해도 되는 주장과 말하면 위험한 주장을 팀 공유용으로 정리한 것이다. 핵심 목적은 발표자가 같은 기준으로 설명하고, 질의응답에서 결과를 과장하지 않도록 만드는 것이다.

## 1. Executive Summary

이번 프로젝트의 중심 주장은 다음 한 문장으로 정리된다.

> Pilot assignment is a balance between SINR preservation and pilot-overhead reduction.

Cell-free massive MIMO에서는 여러 AP가 여러 UE를 동시에 serving한다. UE 수가 orthogonal pilot 수보다 많아지면 pilot reuse가 필요하고, 같은 pilot을 쓰는 UE들의 channel estimate가 섞이는 pilot contamination 문제가 생긴다. 동시에 spectral efficiency(SE)는 `1 - tau_p / tau_c` prelog factor를 포함하므로, pilot 수를 줄이면 데이터 전송에 쓸 수 있는 coherence block 비율이 커진다.

따라서 좋은 방법은 단순히 pilot 수를 줄이는 것이 아니다. UE clustering, AP pruning, beam-domain conflict graph를 통해 pilot overhead를 줄이되, SINR이 무너질 정도로 중요한 channel structure를 버리지 않아야 한다.

최종 발표의 메인 비교 대상은 여섯 개다.

| Method name | Role | Meaning |
| --- | --- | --- |
| Random | Reference | structure를 쓰지 않는 기준 |
| Gao Matching | Reference | AP-domain many-to-many matching |
| Mussbah Beam Graph | Reference | active/moderate beam 기반 binary conflict graph |
| AP-Top-N (N=8) | Proposed | UE별 strongest AP Top-N 기반 adaptive coloring |
| Beam-Weighted Threshold | Proposed | active-active conflict에 더 큰 weight를 주는 beam graph |
| Beam-Resource Matching | Proposed | AP-beam resource 단위로 UE를 matching하고 adaptive pilot count를 정하는 방식 |

## 2. Main Figure Set

발표 본문에는 아래 디렉토리의 그림을 사용한다.

- `figures/presentation_6method/presentation_clean_load_crossover_se.png`
- `figures/presentation_6method/presentation_clean_load_crossover_ee.png`
- `figures/presentation_6method/presentation_clean_pilot_count_vs_k.png`

백업 또는 질의응답용 그림은 아래를 사용한다.

- `figures/presentation_6method/presentation_latest_6method_p5_throughput_vs_k.png`
- `figures/presentation_6method/presentation_latest_6method_ecdf_throughput_k50.png`
- `figures/presentation_gao_stress_L100_tau3/gao_stress_avg_se_vs_k.png`
- `figures/presentation_gao_stress_L100_tau3/gao_stress_p5_throughput_vs_k.png`
- `figures/presentation_gao_stress_L100_tau3/gao_stress_ecdf_throughput_k45.png`

## 3. Main Six-Method Result

Source: `figures/presentation_6method/presentation_mjh_6method_k_sweep.csv`

환경은 `L=200`, `N=8`, `K=25,30,35,40,45,50`, `tau_c=150`, `tau_p_design=15`, 200 setups이다. 그래프 범례는 최종 발표용 여섯 method로 제한했다.

K=50 기준 핵심 수치는 다음과 같다.

| Method | Mean SE vs Random | P5 throughput vs Random | EE proxy vs Random | Mean actual tau_p |
| --- | ---: | ---: | ---: | ---: |
| Gao Matching | `-0.02%` | `+0.43%` | `-0.02%` | `15.00` |
| Mussbah Beam Graph | `-23.24%` | `-22.26%` | `-18.75%` | `45.76` |
| AP-Top-N (N=8) | `+5.35%` | `+6.32%` | `+5.29%` | `7.79` |
| Beam-Weighted Threshold | `-2.09%` | `-1.29%` | `+3.30%` | `17.06` |
| Beam-Resource Matching | `+6.66%` | `+7.07%` | `+12.35%` | `5.29` |

해석:

1. `Beam-Resource Matching`이 현재 최종 six-method 결과에서 가장 설득력 있는 방향이다. 평균 SE, 95%-likely throughput, EE proxy가 모두 Random보다 높고, mean actual `tau_p`도 5.29로 낮다.
2. `AP-Top-N (N=8)`은 단순한 AP-domain pruning 방식인데도 K=50까지 Random보다 높은 SE와 P5 throughput을 유지한다. 발표에서는 "low-information AP-domain baseline/proposed method"로 설명하기 좋다.
3. `Beam-Weighted Threshold`는 중요한 cautionary case다. 낮은 K에서는 괜찮지만, K=40부터 평균 SE가 Random 아래로 내려간다. K=50에서는 actual `tau_p=17.06`으로 design budget 15를 넘는다. 즉 weighted beam conflict 자체가 틀렸다는 뜻이 아니라, adaptive pilot-count rule이 load에서 커지는 문제를 제어해야 한다는 뜻이다.
4. `Mussbah Beam Graph`는 이 환경에서 conflict graph가 너무 dense해진다. K=50에서 actual `tau_p=45.76`까지 커지므로 prelog 손실이 크다.
5. `Gao Matching`은 main environment에서 Random과 거의 같다. 이는 Gao가 의미 없다는 뜻이 아니라, 이 evaluator와 `tau_p_design=15` 조건에서는 Gao의 AP quota가 실제로 binding되지 않아 AP selection 구조가 Random 기준과 거의 같아지기 때문이다.

## 4. Why Gao Looks Like Random In The Main Setting

메인 환경에서 Gao와 Random이 붙는 것은 그래프가 예쁘지 않은 문제가 아니라, 실험 조건상 자연스러운 결과에 가깝다.

점검 결과, `tau_p_design=15` 조건에서는 Gao AP matching의 quota가 거의 걸리지 않는다. K=50에서도 selected AP의 load가 quota 15보다 충분히 낮아, Gao가 만드는 `mu` mask가 baseline AP mask와 거의 같아진다. 이 경우 pilot index assignment만 조금 달라지고, serving AP/RF/edge 구조가 Random과 거의 같아져 평균 SE와 EE가 붙는다.

발표에서 이렇게 말하면 된다.

> In the main environment, Gao Matching is included as an AP-domain reference. It stays close to Random because the AP quota is not resource-constrained enough to change the serving mask. When we make the pilot/AP resource constraint tighter, Gao starts to separate, which is shown only as a backup diagnostic.

## 5. Gao-Stress Diagnostic

Source: `figures/presentation_gao_stress_L100_tau3/gao_stress_6method_summary.csv`

환경은 `L=100`, `N=8`, `K=25,30,35,40,45,50`, `tau_c=150`, `tau_p_design=3`, 200 setups, bandwidth 20 MHz이다.

K=50 기준 Gao vs Random은 다음과 같다.

- Mean SE: `+1.80%`
- P5 throughput: `+10.38%`
- EE proxy: `-1.37%`
- Edge count: `-25.05%`
- Mean RF/AP resources: `+0.37`

이 결과의 의미는 제한적이다. `tau_p=3`은 Gao의 동작 메커니즘을 보기 위한 stress setting이다. K=25-50에서 realistic main setting이라고 주장하면 안 된다. 다만 "Gao가 Random과 항상 같은 방법은 아니며, resource constraint가 binding될 때는 lower-tail throughput에서 차이가 난다"는 설명에는 사용할 수 있다.

[Inference] 더 현실적인 방식으로 Gao 차이를 보고 싶다면 `tau_p=15`를 유지하고 K를 더 크게 늘리는 sweep이 낫다. 예를 들어 `K=50,75,100,125,150` 같은 high-load setting이 후보가 될 수 있다. 이 실험은 아직 실행하지 않았으므로 발표 본문 주장으로 쓰면 안 된다.

## 6. Recommended Presentation Story

발표 흐름은 다음 순서가 가장 방어 가능하다.

1. Cell-free massive MIMO는 distributed AP들이 cell boundary 없이 UE들을 공동 serving하는 구조다.
2. Channel estimation은 uplink pilot에 의존하고, coherence block 안에서 pilot이 차지하는 길이 `tau_p`는 데이터 전송 자원을 줄인다.
3. UE가 많아지면 pilot reuse가 필요하고, 같은 pilot을 쓰는 UE들이 겹치는 AP/beam을 공유하면 pilot contamination이 커진다.
4. 그래서 pilot assignment는 conflict graph 문제로 볼 수 있다.
5. Gao는 AP-domain matching, Mussbah는 beam-domain conflict graph라는 두 축을 제공한다.
6. 우리는 이 두 축을 같은 evaluator에 놓고, AP-Top-N, Beam-Weighted Threshold, Beam-Resource Matching으로 확장했다.
7. 결과적으로 "pilot count를 줄이는 것" 자체가 답은 아니다. conflict graph를 잘 줄여서 `tau_p`를 낮추되, SINR-side 손실이 작아야 SE가 오른다.
8. 현재 최종 결과에서는 Beam-Resource Matching과 AP-Top-N이 그 균형을 가장 잘 보여준다.

## 7. What To Say

짧게 설명해야 할 때는 이렇게 말하면 된다.

> We compared AP-domain and beam-domain pilot-assignment ideas under one six-method evaluator. Gao Matching is the AP-domain matching reference, Mussbah Beam Graph is the beam-domain graph reference, and our proposed family changes how the conflict graph is sparsified. The main result is that adaptive pilot assignment helps only when it reduces pilot overhead without damaging the useful channel structure too much. In the final K-sweep, Beam-Resource Matching and AP-Top-N keep positive SE and EE margins, while Beam-Weighted Threshold shows that a weighted graph still needs a controlled pilot-count rule under load.

## 8. What Not To Claim

아래 주장은 하지 않는 것이 맞다.

- "Fewer pilots are always better."
  틀리다. pilot 수를 줄이다가 SINR이 무너지면 SE는 떨어진다.
- "Beam-domain methods always beat AP-domain methods."
  현재 결과는 method-specific이다. Beam-Weighted는 K=40부터 평균 SE가 Random 아래로 내려간다.
- "Gao is useless because it equals Random."
  부정확하다. main environment에서 quota가 binding되지 않았기 때문에 붙은 것이다. `tau_p=3` stress에서는 Gao가 lower-tail throughput에서 차이를 보인다.
- "`tau_p=3` is our practical recommendation."
  아니다. 이 설정은 diagnostic/stress setting이다.
- "EE is a full energy model."
  현재 발표의 EE는 proxy로 설명해야 한다.
- "The result proves SINR improvement."
  현재 주장은 prelog gain과 SINR degradation의 balance다. SINR 자체가 증가했다고 말하려면 별도 SINR/NMSE diagnostic이 필요하다.

## 9. Q&A Notes

**Q. Why did we use Top-N instead of beam-domain only?**
Top-N은 AP-domain에서 필요한 정보가 적은 pruning rule이다. Beam-domain 방법이 더 rich한 channel structure를 쓰는 것은 맞지만, Top-N은 low-information baseline/proposed method로 가치가 있다.

**Q. Why does Gao overlap Random?**
Main setting에서는 AP quota가 binding되지 않아 serving mask가 거의 바뀌지 않는다. 그래서 평균 SE/EE가 Random과 붙는다. Resource constraint를 작게 만들면 Gao가 lower-tail throughput에서 분리된다.

**Q. What is the best current direction?**
최종 six-method 결과 기준으로는 Beam-Resource Matching이 가장 방어 가능하다. AP-Top-N은 단순하면서도 positive margin을 유지한다. Beam-Weighted Threshold는 개선 방향이라기보다 pilot-count control이 중요하다는 lesson으로 말하는 편이 낫다.

**Q. What is the final conclusion?**
Good UE clustering and AP/beam pruning should balance SINR preservation against pilot-count reduction. The practical value is not "higher SINR by itself"; it is reducing pilot overhead while keeping SINR-side loss small enough that the prelog gain survives.

## 10. Remaining Caveats

- Final six-method plots do not include bootstrap confidence intervals. Significance wording은 피한다.
- Gao high-load realistic sweep (`tau_p=15`, larger K) has now been run. It did not produce a large mean-SE Gao/Random separation; at `K=300`, Gao is `+0.07%` on mean SE and `+1.52%` on P5 throughput.
- EE is a simplified proxy, not a fully coupled network energy model.
- SINR/NMSE decomposition is not yet included. Therefore "SINR preserved"는 결과 해석으로만 말하고, direct measured SINR claim으로 말하지 않는다.
