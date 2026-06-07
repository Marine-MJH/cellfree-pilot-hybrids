# Presentation Plan

최종 갱신: 2026-06-08. 목표 발표 시간: 본문 18-20분, Q&A 별도.

## 1. Final Narrative

> **Pilot assignment in cell-free massive MIMO is not a problem of simply using fewer pilots; it is a balance between pilot-overhead reduction and preserving the channel structure needed for SINR.**

교수님이 cell-free massive MIMO를 모른다는 전제로 시작한다. 발표는 "기존 논문 재현"이 아니라, 다음 연구 질문을 따라가야 한다.

1. Cell-free massive MIMO에서는 많은 AP가 많은 UE를 cell boundary 없이 공동 serving한다.
2. 이 구조는 coverage와 macro-diversity를 주지만, AP-UE channel estimation 수가 커진다.
3. Coherence block 안에서 pilot 길이 `tau_p`가 커지면 데이터 전송 시간이 줄고, 너무 작으면 pilot contamination이 커진다.
4. 따라서 pilot assignment는 "누가 같은 pilot을 써도 되는가"를 정하는 conflict graph 문제로 볼 수 있다.
5. Gao는 AP-domain matching, Mussbah는 beam-domain graph coloring이라는 출발점을 준다.
6. 우리는 AP-Top-N, Beam-Weighted Threshold, Beam-Resource Matching으로 conflict graph를 sparsify하는 method family를 비교했다.
7. 최종 결과는 Beam-Resource Matching과 AP-Top-N이 moderate load와 antenna sweep에서 가장 방어 가능하다는 것이다.
8. High-K stress test는 모든 adaptive method가 무조건 좋은 것이 아니며, pilot-count control이 없으면 무너질 수 있음을 보여준다.

## 2. What To Strengthen

발표에서 강화할 부분:

- System model: cell-free 구조, pilot channel estimation, coherence block prelog.
- Problem framing: pilot contamination과 pilot overhead가 동시에 존재한다는 tradeoff.
- Method family: 개인 작업 분담이 아니라 AP-domain/beam-domain conflict signal을 바꿔보는 공동 방법군.
- Main result: `Beam-Resource Matching`은 K=50에서 SE `+6.66%`, EE proxy `+12.35%`, P5 throughput `+7.07%`.
- Robustness: N=1..8 antenna sweep에서 Beam-Resource는 모든 N에서 평균 SE 1위이고, N=8에서 SE `+6.57%`, EE proxy `+12.01%`.
- Limitation: high-K에서는 AP-Top-N과 Beam-Resource도 eventually Random 아래로 내려갈 수 있다. 이건 결론을 더 강하게 만든다: fewer pilots alone is not the answer.

줄일 부분:

- Gao를 main winner처럼 설명하지 않는다. Same-environment에서는 Random과 거의 붙는다.
- Mussbah를 main comparison plot에서 과하게 강조하지 않는다. 고부하에서는 `tau_p > tau_c`로 SE가 0에 가까워져 축을 망가뜨린다.
- `tau_p=3` Gao-stress는 backup diagnostic으로만 둔다.
- tau_p sweep은 본문에서 빼고, 질문이 오면 "diagnostic only"라고 답한다.
- significance/CI 표현은 쓰지 않는다. 현재 본문 그래프는 200 setups 평균 비교다.

## 3. Slide Structure

| # | Title | Time | Figure / asset | Main point |
| ---: | --- | ---: | --- | --- |
| 1 | Title | 0.4 min | none | Topic and team |
| 2 | Cell-Free Massive MIMO: Basic Picture | 1.2 min | TikZ AP/UE/CPU sketch | Distributed APs jointly serve UEs without fixed cell boundaries |
| 3 | System Model: Channels and Coherence Block | 1.4 min | channel equation + coherence block | Pilot length directly reduces data symbols |
| 4 | Uplink Pilots and Channel Estimation | 1.5 min | pilot observation equation | Same pilot reuse mixes channel estimates |
| 5 | Pilot Contamination from Many-to-Many Serving | 1.5 min | conflict graph sketch | Many-to-many serving creates dense reuse conflicts |
| 6 | Design Tradeoff: Contamination vs Overhead | 1.3 min | SE formula | The problem is a balance, not "minimize pilots" |
| 7 | Starting Point: Gao and Mussbah | 1.2 min | comparison table | Existing AP-domain and beam-domain ideas motivate our method family |
| 8 | Proposed Method Family | 1.5 min | method diagrams | AP-Top-N, Beam-Weighted, Beam-Resource are conflict-sparsification variants |
| 9 | Method Map | 0.8 min | method table | Six methods, reduced reference set |
| 10 | Experimental Setup | 0.7 min | setup table | Same-environment comparison, 200 setups |
| 11 | Main Result: Moderate User Load | 1.7 min | `figures/presentation_6method/presentation_clean_load_crossover_se.png` | Beam-Resource and AP-Top-N stay above Random through K=50 |
| 12 | Mechanism: Pilot Count vs Channel Structure | 1.4 min | `figures/presentation_6method/presentation_clean_pilot_count_vs_k.png` | Resource/Top-N reduce pilots; Mussbah and Beam-Weighted expose over-dense graph problems |
| 13 | Antenna Sweep: Robustness Across N | 1.7 min | `figures/presentation_n_sweep_6method/n_sweep_avg_se_vs_n.png`, `n_sweep_avg_ee_vs_n.png` | Beam-Resource remains strongest across N=1..8 |
| 14 | Stress Test: Very High User Load | 1.4 min | `figures/presentation_high_k_6method_no_mussbah/high_k_5method_avg_se_vs_k.png` | High-K reveals the operating range and limitations |
| 15 | Result Synthesis | 1.1 min | compact table | What each method teaches |
| 16 | Conclusion | 0.8 min | none | Balance pilot overhead against channel-structure preservation |

Backup slides:

- Gao reproduction anchor: `figures/gao_fig3_vs_pilot_number_final200.png`
- Gao-stress diagnostic: `figures/presentation_gao_stress_L100_tau3/gao_stress_p5_throughput_vs_k.png`
- Full high-K plot with Mussbah if someone asks why it was omitted.

## 4. Final Figure Set

Main deck:

- `figures/presentation_6method/presentation_clean_load_crossover_se.png`
- `figures/presentation_6method/presentation_clean_pilot_count_vs_k.png`
- `figures/presentation_n_sweep_6method/n_sweep_avg_se_vs_n.png`
- `figures/presentation_n_sweep_6method/n_sweep_avg_ee_vs_n.png`
- `figures/presentation_high_k_6method_no_mussbah/high_k_5method_avg_se_vs_k.png`

Backup / Q&A:

- `figures/presentation_6method/presentation_clean_load_crossover_ee.png`
- `figures/presentation_6method/presentation_latest_6method_p5_throughput_vs_k.png`
- `figures/presentation_high_k_6method/high_k_avg_se_vs_k.png`
- `figures/presentation_high_k_6method/high_k_pilot_count_vs_k.png`
- `figures/presentation_gao_stress_L100_tau3/gao_stress_p5_throughput_vs_k.png`
- `figures/gao_fig3_vs_pilot_number_final200.png`

## 5. Headline Numbers

### Moderate K Sweep

Source: `figures/presentation_6method/presentation_mjh_6method_k_sweep.csv`.

Environment: `L=200`, `N=8`, `K=25,30,35,40,45,50`, `tau_c=150`, `tau_p_design=15`, 200 setups.

At `K=50`:

| Method | Mean SE vs Random | P5 throughput vs Random | EE proxy vs Random | Mean actual tau_p |
| --- | ---: | ---: | ---: | ---: |
| Gao Matching | `-0.02%` | `+0.43%` | `-0.02%` | `15.00` |
| Mussbah Beam Graph | `-23.24%` | `-22.26%` | `-18.75%` | `45.76` |
| AP-Top-N (N=8) | `+5.35%` | `+6.32%` | `+5.29%` | `7.79` |
| Beam-Weighted Threshold | `-2.09%` | `-1.29%` | `+3.30%` | `17.06` |
| Beam-Resource Matching | `+6.66%` | `+7.07%` | `+12.35%` | `5.29` |

### Antenna Sweep

Source: `figures/presentation_n_sweep_6method/n_sweep_6method_summary.csv`.

Environment: `L=200`, `K=50`, `N=1..8`, `tau_c=150`, `tau_p_design=15`, 200 setups.

At `N=8`:

| Method | Mean SE vs Random | P5 throughput vs Random | EE proxy vs Random | Mean actual tau_p |
| --- | ---: | ---: | ---: | ---: |
| Gao Matching | `-0.07%` | `-0.15%` | `-0.07%` | `15.00` |
| Mussbah Beam Graph | `-22.97%` | `-22.93%` | `-18.64%` | `45.41` |
| AP-Top-N (N=8) | `+5.25%` | `+5.13%` | `+5.19%` | `7.86` |
| Beam-Weighted Threshold | `-2.14%` | `-2.72%` | `+3.02%` | `17.13` |
| Beam-Resource Matching | `+6.57%` | `+5.55%` | `+12.01%` | `5.39` |

Across `N=1..8`, Beam-Resource Matching is the best mean-SE method at every N. Top-N is competitive and simpler; it is often best or close on EE for small to mid N.

### High-K Stress Test

Source: `figures/presentation_high_k_6method/high_k_6method_summary.csv` and `figures/presentation_high_k_6method_no_mussbah/high_k_5method_summary.csv`.

Environment: `L=200`, `N=8`, `K=50,100,150,200,250,300`, `tau_c=150`, `tau_p_design=15`, 200 setups.

Key readings:

- Gao remains close to Random even at K=300: mean SE `+0.07%`, P5 throughput `+1.52%`.
- Beam-Resource stays positive through K=200, then crosses below Random at K=250.
- AP-Top-N is positive at K=50 and K=100, then crosses below Random at K=150.
- Mussbah is not plotted in the main high-K slide because its actual tau_p exceeds tau_c from K=200 onward, making SE collapse to zero.

## 6. Final Claims

Safe claims:

- Adaptive pilot assignment helps when it reduces pilot overhead without damaging useful channel structure too much.
- Beam-Resource Matching is the strongest current direction in this evaluator.
- AP-Top-N is a useful simple AP-domain method with low information requirements.
- Beam-Weighted Threshold and Mussbah show the failure mode: dense conflict graphs can increase actual pilot count and erase the prelog benefit.
- Gao is a meaningful AP-domain reference, but under this same-environment evaluator its effect is small unless the resource constraint is artificially tightened.

Unsafe claims:

- Do not say "fewer pilots are always better."
- Do not say "beam-domain always wins."
- Do not say Gao was fully reproduced paper-exactly.
- Do not say the EE metric is a complete network energy model.
- Do not say SE gain proves SINR improvement; current evidence supports a balance interpretation.

## 7. Closing Sentence

Use this as the final slide sentence:

> The useful design direction is not simply minimizing pilot count; it is building a conflict graph that removes weak conflicts while preserving enough channel structure for the prelog gain to survive.
