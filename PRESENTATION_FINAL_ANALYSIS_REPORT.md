# Final Presentation Analysis Report

작성일: 2026-06-08

이 문서는 `figures/` 안의 발표용 subdirectory 결과를 종합해, 최종 발표에서 어떤 주장을 중심에 놓고 어떤 결과를 줄여야 하는지 정리한다.

## 1. Executive Summary

최종 방향은 명확하다.

> 이 프로젝트는 cell-free massive MIMO에서 pilot assignment를 conflict graph sparsification 문제로 보고, pilot overhead를 줄이면서 channel structure를 얼마나 보존할 수 있는지 비교했다.

현재 결과에서 가장 방어 가능한 주력 방법은 `Beam-Resource Matching`이다. `AP-Top-N (N=8)`은 단순한 AP-domain 방법인데도 moderate load에서 안정적인 gain을 유지하므로, "low-information practical method"로 설명하기 좋다. 반대로 `Beam-Weighted Threshold`와 `Mussbah Beam Graph`는 중요한 실패 사례다. conflict graph가 너무 dense해지면 actual pilot count가 커지고, `1 - tau_p / tau_c` prelog gain이 사라진다.

`Gao Matching`은 same-environment comparison에서는 거의 Random과 붙는다. 이는 발표에서 약점이 아니라 기준점으로 다루어야 한다. Gao는 AP-domain matching reference이고, 본 프로젝트의 핵심 contribution은 Gao 자체를 이기는 것이 아니라 AP-domain/beam-domain conflict signal을 바꿔 pilot overhead와 channel preservation의 균형을 찾은 것이다.

## 2. Figure Directories

발표용 결과는 아래 subdirectory들에 정리되어 있다.

| Directory | Role | Main use |
| --- | --- | --- |
| `figures/presentation_6method/` | Main moderate-load comparison | 본문 핵심 결과 |
| `figures/presentation_n_sweep_6method/` | Antenna-count robustness | 본문 강화 결과 |
| `figures/presentation_high_k_6method_no_mussbah/` | High-K stress without axis collapse | 본문 또는 backup stress test |
| `figures/presentation_high_k_6method/` | Full high-K with Mussbah | backup; Mussbah collapse 설명 |
| `figures/presentation_gao_stress_L100_tau3/` | Gao diagnostic with small tau_p | backup only |

앞으로 새 figure directory를 만들 때는 반드시 `README.md`에 실험 세팅을 적는다. 현재 새로 만든 `presentation_6method`, `presentation_high_k_6method`, `presentation_high_k_6method_no_mussbah`, `presentation_n_sweep_6method`는 이 규칙을 따른다.

## 3. Main Moderate-Load Result

Source: `figures/presentation_6method/presentation_mjh_6method_k_sweep.csv`

Environment:

- `L=200`, `N=8`
- `K=25,30,35,40,45,50`
- `tau_c=150`, design `tau_p=15`
- 200 setups
- power control: full

At `K=50`:

| Method | Mean SE vs Random | P5 throughput vs Random | EE proxy vs Random | Mean actual tau_p |
| --- | ---: | ---: | ---: | ---: |
| Gao Matching | `-0.02%` | `+0.43%` | `-0.02%` | `15.00` |
| Mussbah Beam Graph | `-23.24%` | `-22.26%` | `-18.75%` | `45.76` |
| AP-Top-N (N=8) | `+5.35%` | `+6.32%` | `+5.29%` | `7.79` |
| Beam-Weighted Threshold | `-2.09%` | `-1.29%` | `+3.30%` | `17.06` |
| Beam-Resource Matching | `+6.66%` | `+7.07%` | `+12.35%` | `5.29` |

Interpretation:

1. `Beam-Resource Matching` is the primary positive result. It reduces actual pilot count to about 5.29 while keeping enough channel structure to improve mean SE, P5 throughput, and EE proxy.
2. `AP-Top-N` is the simple method worth emphasizing. It needs only AP-domain large-scale information but still gives positive SE and P5 gains.
3. `Beam-Weighted Threshold` is not a main winner. It becomes a warning: weighted beam conflicts are not enough if the pilot-count rule lets tau_p exceed the design budget.
4. `Mussbah Beam Graph` becomes too dense in this evaluator. Its actual tau_p reaches 45.76 at K=50, which strongly hurts prelog.
5. `Gao Matching` is almost identical to Random in this setting. Do not oversell it.

## 4. Antenna Sweep Result

Source: `figures/presentation_n_sweep_6method/n_sweep_6method_summary.csv`

Environment:

- `L=200`, `K=50`
- `N=1,2,3,4,5,6,7,8`
- `tau_c=150`, design `tau_p=15`
- 200 setups
- power control: full

At `N=8`:

| Method | Mean SE vs Random | P5 throughput vs Random | EE proxy vs Random | Mean actual tau_p |
| --- | ---: | ---: | ---: | ---: |
| Gao Matching | `-0.07%` | `-0.15%` | `-0.07%` | `15.00` |
| Mussbah Beam Graph | `-22.97%` | `-22.93%` | `-18.64%` | `45.41` |
| AP-Top-N (N=8) | `+5.25%` | `+5.13%` | `+5.19%` | `7.86` |
| Beam-Weighted Threshold | `-2.14%` | `-2.72%` | `+3.02%` | `17.13` |
| Beam-Resource Matching | `+6.57%` | `+5.55%` | `+12.01%` | `5.39` |

Cross-N insight:

- `Beam-Resource Matching` is best on mean SE for every tested N.
- `AP-Top-N` is consistently positive and remains close to the best method.
- `Beam-Weighted Threshold` is unstable: it can be positive at low N, but often crosses below Random as actual tau_p grows.
- `Mussbah Beam Graph` consistently uses around 43-47 pilots and loses to Random across N.
- `Gao Matching` remains a reference line, not a differentiating method.

Presentation value:

This is the strongest new figure for the final deck. It shows that the result is not a one-off at `N=8`; the method ranking is stable as antenna count changes.

## 5. High-K Stress Test

Sources:

- `figures/presentation_high_k_6method/high_k_6method_summary.csv`
- `figures/presentation_high_k_6method_no_mussbah/high_k_5method_summary.csv`

Environment:

- `L=200`, `N=8`
- `K=50,100,150,200,250,300`
- `tau_c=150`, design `tau_p=15`
- 200 setups

Key result:

| K | Gao SE vs Random | Gao P5 vs Random | AP-Top-N SE vs Random | Beam-Resource SE vs Random |
| ---: | ---: | ---: | ---: | ---: |
| 50 | `-0.04%` | `-0.82%` | `+5.28%` | `+6.62%` |
| 100 | `-0.04%` | `+1.07%` | `+1.81%` | `+4.44%` |
| 150 | `-0.01%` | `+0.18%` | `-1.50%` | `+2.65%` |
| 200 | `+0.00%` | `+0.28%` | `-4.62%` | `+1.05%` |
| 250 | `+0.04%` | `+0.92%` | `-7.34%` | `-0.16%` |
| 300 | `+0.07%` | `+1.52%` | `-10.41%` | `-0.72%` |

Interpretation:

1. High-K does not rescue Gao as a strong main result. Even at K=300, mean SE gain is only `+0.07%`.
2. Gao shows a small lower-tail effect at high K: P5 throughput is `+1.52%` at K=300. This is real but too small to anchor the presentation.
3. Beam-Resource is useful through K=200, then crosses below Random at K=250. This is a useful operating-range lesson.
4. AP-Top-N is simpler but loses earlier, crossing below Random around K=150.
5. Mussbah is removed from the main high-K plot because actual tau_p exceeds tau_c from K=200 onward, making SE collapse to zero. Including it compresses the axis and hides the comparison among the other methods.

Presentation value:

Use high-K as a stress test, not as the headline. The message is: adaptive assignment has an operating range; pilot-count control becomes more important as K grows.

## 6. What To Emphasize In The Talk

Strong direction:

- "We are not proposing one isolated algorithm. We compare a family of conflict-sparsification rules."
- "The useful gain comes from reducing pilot overhead while keeping the important AP/beam structure."
- "Beam-Resource Matching is the strongest current rule because it keeps actual tau_p low without losing too much channel structure."
- "AP-Top-N is attractive because it is simpler and still gives stable positive gains under moderate load."

Good professor-facing sentence:

> We started from AP-domain matching and beam-domain graph coloring, then asked which conflict signal produces the best pilot-overhead/SINR tradeoff under a unified evaluator.

## 7. What To Reduce

Reduce:

- Gao reproduction details in the main body. Put them in backup.
- Mussbah high-K failure in the main body. Explain briefly; show full plot only if asked.
- tau_p=3 stress result. It is a diagnostic, not a practical conclusion.
- Too many baselines. Main deck should use the six named methods only, and high-K main plot should use five after removing Mussbah.

## 8. Recommended Final Deck Steering

Main body should be:

1. Teach cell-free massive MIMO and pilot contamination.
2. Frame the tradeoff with the SE formula.
3. Introduce Gao and Mussbah as the two reference axes.
4. Introduce our method family.
5. Show moderate-load K-sweep.
6. Show pilot-count mechanism.
7. Show N-sweep robustness.
8. Show high-K stress as limitation.
9. Conclude with "balance, not simply fewer pilots."

This is stronger than trying to claim Gao becomes strong. The high-K experiment showed the opposite: Gao remains close to Random. Do not force the story there.

## 9. Q&A Preparation

**Why does Gao stay near Random?**

In this unified evaluator, Gao's AP-domain matching changes the serving structure only slightly under the default resource budget. At high K, it reduces edges a little and improves P5 throughput slightly, but the mean-SE effect remains small.

**Why remove Mussbah from the high-K plot?**

Because its actual pilot count exceeds the coherence block from K=200 onward. That makes its SE collapse to zero and compresses the y-axis. The full plot is still available as backup.

**Which method is the best?**

Beam-Resource Matching is the best current direction in this evaluator. It is consistently strongest on mean SE in the N-sweep and gives the best moderate-load K=50 result.

**Is the answer simply using fewer pilots?**

No. AP-Top-N and Beam-Resource work because they reduce pilots while preserving useful structure. Beam-Weighted and Mussbah show that a dense or poorly controlled graph can increase tau_p and lose.

**What is the research conclusion?**

The key design problem is selecting the right conflict graph. The graph should remove weak conflicts, keep strong channel structure, and keep the resulting pilot count under control.
