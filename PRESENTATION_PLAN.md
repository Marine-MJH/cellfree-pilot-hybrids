# Presentation Plan

최종 갱신: 2026-06-07. 목표 발표 시간: 본문 18-20분, Q&A 별도.

## 1. One-Sentence Narrative

> **Pilot assignment is a balance between SINR preservation and pilot-overhead reduction.**

발표는 개인별 작업 분담이 아니라 **공동 제안한 method family**로 설명한다.

20분 자유주제 연구발표이므로, 이미 cell-free massive MIMO를 아는 사람을 가정하면 안 된다. 앞부분은 논문 발표처럼 system model부터 쌓는다.

1. Cell-free massive MIMO는 여러 distributed AP가 cell boundary 없이 여러 UE를 공동으로 serving하는 구조다.
2. AP는 uplink pilot을 통해 UE-AP channel을 추정하고, 이 추정값으로 beamforming/combining과 SE 계산을 한다.
3. UE 수가 orthogonal pilot 수보다 많으면 pilot reuse가 필요하고, 같은 pilot을 쓰는 UE들의 channel estimate가 섞인다.
4. 다대다 AP-UE 연결 때문에 "누가 누구와 pilot을 공유해도 되는가"가 dense conflict graph 문제가 된다.
5. 좋은 pilot assignment는 UE clustering / AP-beam pruning으로 실제 pilot 수를 낮추되, 강한 채널 구조는 유지해야 한다.
6. 이번 프로젝트는 AP-domain과 beam-domain에서 conflict graph를 줄이는 여러 방법을 비교했다.
7. Current evidence points to adaptive pilot-count reduction as the right direction; under increasing load, a method can lose to Random if its conflict graph becomes too dense or its adaptive pilot count grows too much.

## 2. Method Names For Slides And Legends

메인 발표와 그래프 범례에서는 아래 6개만 사용한다. 나머지 GC/Structured/TopAP-bisect/Hybrid#4/weighted-default/weighted-power는 CSV와 backup material에는 남기되 본문 그래프에서 제외한다.

| Slide / legend name | Role | Short meaning |
| --- | --- | --- |
| **Random** | Reference | no structure-aware assignment |
| **Gao Matching** | Reference | AP-domain many-to-many matching |
| **Mussbah Beam Graph** | Reference | binary active/moderate beam graph |
| **AP-Top-N Adaptive** | Proposed | Top-N AP overlap graph + adaptive coloring |
| **Beam-Weighted Threshold** | Proposed | weighted active/moderate beam graph + threshold |
| **Beam-Resource Matching** | Proposed | AP-beam resource matching + adaptive pilot count |

Regenerate clean figures after the same-environment K-sweep finishes:

```bash
python experiments/presentation_make_clean_figures.py
```

## 3. Final Main Deck: 14 Slides, 20 Minutes

| # | Title | Time | Figure / asset | Main point | Do not say |
| ---: | --- | ---: | --- | --- | --- |
| 1 | Title | 0.5 min | none | Topic and team | Do not lead with every scheme name |
| 2 | Cell-Free Massive MIMO: Basic Picture | 1.3 min | TikZ AP/UE/CPU sketch | Many distributed APs jointly serve many UEs | Do not assume "cell-free" is already clear |
| 3 | System Model: Channels and Coherence Block | 1.4 min | channel + coherence-block equations | Channel estimation consumes part of each coherence block | Do not jump directly to algorithms |
| 4 | Uplink Pilots and Channel Estimation | 1.7 min | pilot observation equation | Same pilot reuse mixes channel observations | Do not overderive MMSE details |
| 5 | Pilot Contamination from Many-to-Many Serving | 1.8 min | conflict graph sketch | Dense AP/UE overlap makes reuse conflicts frequent | Do not frame contamination as only a cellular edge issue |
| 6 | Design Tradeoff: Contamination vs Overhead | 1.3 min | SE formula | `SE = (1 - tau_p/tau_c) log2(1+SINR)` drives the whole story | Do not claim fewer pilots are always better |
| 7 | Starting Point: Gao and Mussbah | 1.2 min | comparison table | Gao and Mussbah motivate AP-domain and beam-domain axes | Do not directly compare their absolute SE numbers |
| 8 | Reproduction Anchor | 1.0 min | `figures/gao_fig3_vs_pilot_number_final200.png` | Gao small-pilot advantage is a useful anchor | Do not claim the whole paper ordering is perfectly recovered |
| 9 | Proposed Method Family | 1.5 min | TikZ method-family diagram | There are multiple proposed methods, not one single hybrid | Do not split the slide into person-specific ownership |
| 10 | Method Map | 0.8 min | method table | Methods differ by domain, conflict signal, and pilot-budget rule | Do not list every evaluated baseline |
| 11 | Main Result: User Load Sweep | 1.8 min | `figures/presentation_6method/presentation_clean_load_crossover_se.png` | AP-Top-N and Beam-Resource remain above Random, while Beam-Weighted crosses below Random under load | Do not insert Gao-style hybrid as a substitute baseline |
| 12 | Mechanism: Pilot Count vs SINR Balance | 1.4 min | `figures/presentation_6method/presentation_clean_pilot_count_vs_k.png` | Pilot-count reduction helps through prelog; Mussbah shows the cost of dense conflicts | Do not say the methods directly increase SINR |
| 13 | Energy Efficiency Under User Load | 1.2 min | `figures/presentation_6method/presentation_clean_load_crossover_ee.png` | Beam-Resource and AP-Top-N keep positive EE gains because they use fewer pilots | Do not treat EE as a fully coupled power-control model |
| 14 | Conclusion | 0.9 min | none | Good UE clustering and AP/beam pruning should balance SINR against pilot-count reduction | Do not oversell "fewer pilots are always better" |

## 4. Headline Numbers To Use

### 4.1 Main Same-Environment Six-Method K-sweep

Source: `figures/presentation_6method/presentation_mjh_6method_k_sweep.csv`.

Environment:

- `K=25,30,35,40,45,50`, `L=200`, `N=8`
- `tau_c=150`, `tau_p_design=15`
- 200 setups
- Weighted threshold 10
- Top-N graph uses `N=8` in the plotted AP-Top-N line
- Evaluator: same six-method AP/beam-domain comparison / same EE proxy

Methods in the K-sweep:

- Random
- Gao Matching
- Mussbah Beam Graph
- AP-Top-N (N=8)
- Beam-Weighted Threshold
- Beam-Resource Matching

Reading:

- Gao Matching stays near Random: at `K=50`, mean SE `-0.02%`, P5 throughput `+0.43%`, EE proxy `-0.02%`.
- AP-Top-N stays positive: at `K=50`, mean SE `+5.35%`, P5 throughput `+6.32%`, EE proxy `+5.29%`, mean actual pilot count `7.79`.
- Beam-Resource Matching stays positive and is the strongest final direction: at `K=50`, mean SE `+6.66%`, P5 throughput `+7.07%`, EE proxy `+12.35%`, mean actual pilot count `5.29`.
- Beam-Weighted Threshold is a cautionary case: it is positive at low load, but crosses below Random from `K=40`; at `K=50`, mean SE `-2.09%` while EE proxy remains `+3.30%` because its selected resources are low.
- Mussbah Beam Graph becomes too dense in this environment: at `K=50`, mean actual pilot count `45.76`, mean SE `-23.24%`, EE proxy `-18.75%`.
- Do not reuse the old MJH `H2GaoGreedy` stress sweep as the main six-method comparison.

### 4.2 Gao-Stress Diagnostic

Source: `figures/presentation_gao_stress_L100_tau3/gao_stress_6method_summary.csv`.

Environment: `L=100`, `N=8`, `K=25,30,35,40,45,50`, `tau_c=150`, `tau_p_design=3`, 200 setups, bandwidth 20 MHz.

Reading:

- This is a diagnostic setting, not the main design point. The small pilot budget makes Gao's AP matching quota bind.
- In this stress setting, Gao separates from Random: at `K=50`, mean SE `+1.80%`, P5 throughput `+10.38%`.
- Gao's EE proxy is still lower than Random at `K=50` (`-1.37%`) because it uses more RF/AP resources.
- Use this figure only if someone asks why Gao looked identical to Random in the main setting.

## 6. Graph And Environment Consistency Checklist

| Priority | Item | Why it matters | Action |
| ---: | --- | --- | --- |
| P0 | No person-specific split in method slides | This is a joint presentation | Use method names only: AP-Top-N, Beam-Weighted, Beam-Resource |
| P0 | Reduced reference set | Too many references obscure the contribution | K-sweep figures use Random, Gao, Mussbah, and three proposed methods |
| P0 | Legend consistency | Scheme names previously differed between plots and slides | Use `presentation_make_clean_figures.py` outputs |
| P0 | Environment labels on result slides | Gao reproduction, same-environment MC, and teammate K-sweep results differ | Put `K,L,N,tau_c,tau_p,setups` in slide text or caption |
| P0 | Keep environment labels visible | Absolute SE across evaluators is not fair | Label K-sweep and mechanism snapshot separately |
| P0 | Do not fake missing references | The main comparison is exactly six methods | Run pure Gao/Mussbah in the load-crossover environment instead of substituting Gao-style hybrid |
| P0 | Reword Gao reproduction | Prior runs support the small-pilot advantage, but paper-exact benchmark ordering was not fully recovered; this same-environment beam-domain evaluator leaves Gao near Random | Say "reproduction anchor", not "strong same-environment baseline" |
| P0 | Treat EE as proxy | Main EE uses active-resource estimation separate from SE serving constraints | Say "EE proxy" |
| P1 | Do not use tau_p sweep in main deck | It distracts from the load-crossover story | Removed from main slides |
| P1 | Add CI for the final 6-method graph if saying significance | The old E4 CI does not automatically cover this final figure | Either run bootstrap on `presentation_main_raw_main_beam20_wt10.csv` or avoid significance wording |
| P1 | State crossover precisely | Only Beam-Weighted crosses below Random in the final same-environment K-sweep | Do not imply all proposed methods cross |
| P2 | Add NMSE / contamination diagnostic only if time allows | It would support the answer to "why does pruning not collapse SINR?" | Backup only; not needed in main story |

## 7. Q&A Lines

1. **Why AP-domain Top-N at all if beam-domain looks stronger?**  
   AP-Top-N Adaptive is a low-information AP-domain sparsification rule. Beam-domain methods use richer channel structure and currently look stronger.

2. **How are the proposed methods different?**  
   AP-Top-N uses strongest AP overlap, Beam-Weighted uses weighted active/moderate beam overlap, and Beam-Resource Matching assigns UE groups through AP-beam resources.

3. **Why does reducing pilot count help?**  
   Because the prelog factor `(tau_c - tau_p) / tau_c` grows. In the final K-sweep, most SE gain is explained by this term; the useful part is that SINR does not visibly collapse in the tested range.

4. **Is the answer simply using fewer pilots?**  
   No. A method can reduce pilots too aggressively and damage SINR. Our current evidence says the strongest methods reduce overhead while keeping the SINR-side loss small in this environment.

5. **Which direction should the team push?**  
   Beam-Resource Matching is the strongest current direction in the final same-environment six-method result. AP-Top-N remains useful as a simple AP-domain method. Beam-Weighted Threshold is useful as a design lesson: weighted beam conflicts help, but the pilot-count rule must not grow past the design budget under load.

## 8. Final Wording

Use this as the final slide / closing sentence:

> The practical value of adaptive pilot assignment is not higher SINR by itself; it is reducing pilot overhead while keeping SINR degradation small enough that the prelog gain survives.
