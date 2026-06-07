# 발표 Main Claim 검토 — Fewer Pilots 가 아니라 Right-Sized Pilot Overhead

작성일: 2026-06-07  
대상: 발표 conclusion 후보인 "파일럿 수가 적을수록 성능이 좋아진다. 단, SINR 이 무너질 정도로 줄이면 안 된다"의 안전성 검토와 발표용 문장 정리.

---

## 0. 결론

원문 claim 은 **방향은 맞지만 그대로 말하면 과장**입니다.

발표에서 써야 할 표현:

> **Reduced-but-sufficient active set 을 만들면 conflict graph 가 sparse 해지고, 실제 필요한 pilot 수가 줄어 coherence block 안의 data 전송 비율이 커진다. 본 실험 범위에서는 이 prelog gain 이 SINR 손실보다 커서 SE/EE 가 개선됐다.**

금지해야 할 표현:

> "파일럿 수가 적을수록 무조건 좋다."

이 표현은 바로 공격받습니다. `tau_p=1`이면 왜 더 좋지 않냐는 질문이 나오고, fixed `tau_p`에서 성능이 안 좋은 scheme도 있기 때문입니다.

---

## 1. Claim 을 정확히 분해

| 요소 | 발표에서 말할 내용 | 상태 |
|---|---|---|
| 관찰 | adaptive scheme 중 실제 `tau_p_actual` 이 낮은 쪽이 mean SE/EE 에서 강함 | 확인됨 |
| 메커니즘 | `SE = (1 - tau_p/tau_c) log2(1 + SINR_eff)` 이므로 `tau_p` 감소는 data prelog 를 키움 | 수식상 명확 |
| 단서 | active AP/beam 을 너무 줄이면 estimation/SINR 손실이 prelog gain 을 넘을 수 있음 | 반드시 말해야 함 |
| 구현 경로 A | AP/beam-side filtering: beam-detect SNR, weighted beam threshold, beam-resource matching | MJH 계열 |
| 구현 경로 B | UE-side filtering: Top-N AP, TopAP conflict graph, Hybrid#3 | 우리 계열 |
| 통합 해석 | 둘 다 "effective serving/conflict graph sparsification" 으로 볼 수 있음 | [Inference] |

정확한 한 문장:

> **The key lever is not blindly minimizing pilot count, but selecting a sparse enough active set that reduces pilot overhead while preserving enough channel quality.**

---

## 2. 숫자로 보는 근거

### 2.1 우리 발표 환경

Source: [`figures/presentation_main_summary_main_beam20_wt10.csv`](figures/presentation_main_summary_main_beam20_wt10.csv)  
환경: K=50, L=200, N=8, `tau_c=150`, `tau_p_design=15`, beam-detect=20 dB, weight-threshold=10, 200 setups x 20 channel samples.

| Scheme | Mean SE | vs Random | P5 SE | Mean `tau_p_actual` | EE proxy | 핵심 해석 |
|---|---:|---:|---:|---:|---:|---|
| Random | 5.375 | 0.00% | 1.142 | 14.94 | 1.440 | fixed-budget baseline |
| Mussbah / weighted default | 5.697 | +5.99% | 1.238 | 6.93 | 2.199 | SNR filtering 으로 sparse graph |
| **MJH weighted-count strict** | **5.833** | **+8.53%** | 1.220 | **3.23** | **2.252** | 가장 aggressive 한 pilot reduction |
| **MJH beam-resource matching** | **5.794** | **+7.80%** | **1.240** | **4.46** | 2.237 | tail SE 까지 가장 안정적 |
| **Hybrid#3 TopAP adaptive** | 5.659 | +5.28% | 1.236 | 7.90 | 1.718 | UE-side Top-N 으로 같은 방향 |
| TopAP bisect | 5.377 | +0.05% | 1.147 | 14.91 | 1.465 | pilot 수를 못 줄이면 SE gain 도 거의 없음 |

**핵심 관찰**:

- `tau_p_actual` 이 15 근처인 fixed/bisect 계열은 mean SE 가 Random 근처에 머뭅니다.
- `tau_p_actual` 이 3-8 수준으로 내려간 adaptive 계열은 mean SE 가 +5-9% 올라갑니다.
- P5 SE 도 adaptive 계열이 Random보다 낮아지지 않았습니다. 즉 이 환경에서는 pruning 이 tail user 를 크게 희생하지 않았습니다.

주의:

- 이 표만으로 "pilot count 단독 인과"를 증명한 것은 아닙니다.
- 다만 prelog ratio 와 measured SE gain 이 거의 맞아떨어져, pilot overhead 가 dominant factor 라는 해석은 강합니다.

### 2.2 MJH 환경

Source: [`MJH/result_final_w2_1_1_thr10_full_200/sweep_K_all_schemes.csv`](MJH/result_final_w2_1_1_thr10_full_200/sweep_K_all_schemes.csv)  
환경: L=100, N=8, `tau_c=100`, `tau_p_design=10`, full power, closed-form SE, 200 setups.

K=30 기준:

| Scheme | Mean SE | vs Random | P5 SE | Mean `tau_p_actual` | EE | 핵심 해석 |
|---|---:|---:|---:|---:|---:|---|
| Random | 3.171 | 0.00% | 0.774 | 10.00 | 1.040 | fixed baseline |
| H3 TopAP adaptive | 3.224 | +1.68% | 0.774 | 8.34 | 1.058 | small pilot reduction |
| Proposed weighted-threshold | 3.233 | +1.96% | 0.781 | 7.42 | 1.128 | beam weighted threshold |
| **MatchingBeamAdaptive** | **3.335** | **+5.18%** | **0.802** | **4.59** | **1.163** | strongest adaptive reduction |
| MatchingBeamFixed | 3.142 | -0.92% | 0.758 | 10.00 | 1.097 | fixed pilot이면 matching 자체는 SE 우위가 아님 |

K-sweep:

| K | Random SE | H3 SE / tau | Proposed SE / tau | MatchingAdaptive SE / tau |
|---:|---:|---:|---:|---:|
| 25 | 3.283 | 3.374 / 7.43 | 3.381 / 6.64 | **3.469 / 4.23** |
| 30 | 3.171 | 3.224 / 8.34 | 3.233 / 7.42 | **3.335 / 4.59** |
| 35 | 3.051 | 3.069 / 9.37 | 3.088 / 8.24 | **3.196 / 5.10** |
| 40 | 2.937 | 2.925 / 10.24 | 2.942 / 9.03 | **3.059 / 5.45** |
| 45 | 2.889 | 2.848 / 11.18 | 2.875 / 9.67 | **2.999 / 5.81** |

**핵심 관찰**:

- MatchingBeamAdaptive 는 K=25-45 전체에서 가장 낮은 `tau_p_actual` 과 가장 높은 SE 를 같이 보입니다.
- H3 TopAP 은 K 가 커지면 `tau_p_actual` 이 10을 넘고, 그때 SE advantage 도 사라집니다.
- Proposed weighted-threshold 는 K=45에서 `tau_p_actual=9.67`로 pilot gain 이 거의 없어지고 SE도 Random보다 낮습니다.

따라서 결론은 "적을수록 좋다"가 아니라 **active-set sparsification 이 충분히 강해서 `tau_p_actual` 을 실제로 낮출 때만 이득이 난다**입니다.

---

## 3. Prelog 로 보는 메커니즘

기본식:

```text
SE_k = (1 - tau_p_actual / tau_c) log2(1 + SINR_eff,k)
```

### 3.1 우리 환경, `tau_c=150`

| Scheme | Mean `tau_p_actual` | Prelog | Prelog vs Random | Observed mean SE vs Random |
|---|---:|---:|---:|---:|
| Random | 14.94 | 0.900 | 0.00% | 0.00% |
| MJH weighted-count strict | 3.23 | 0.979 | +8.67% | +8.53% |
| MJH beam-resource matching | 4.46 | 0.970 | +7.76% | +7.80% |
| Hybrid#3 | 7.90 | 0.947 | +5.21% | +5.28% |

이 표가 발표의 가장 강한 메커니즘 근거입니다. 관측 SE gain 이 prelog gain 과 거의 같은 크기입니다.

[Inference] 이 환경에서는 pilot reduction 으로 얻은 prelog gain 이 SINR 손실보다 컸고, SINR 변화는 1차 효과가 아니었을 가능성이 큽니다.

### 3.2 MJH 환경, `tau_c=100`, K=30

| Scheme | Mean `tau_p_actual` | Prelog | Prelog vs Random | Observed mean SE vs Random |
|---|---:|---:|---:|---:|
| Random | 10.00 | 0.900 | 0.00% | 0.00% |
| MatchingBeamAdaptive | 4.59 | 0.954 | +6.01% | +5.18% |
| Proposed weighted-threshold | 7.42 | 0.926 | +2.87% | +1.96% |
| H3 TopAP adaptive | 8.34 | 0.917 | +1.85% | +1.68% |

여기도 같은 방향입니다. prelog gain 보다 measured gain 이 약간 작습니다. 이 차이는 [Inference] 같은 pilot reuse 증가, serving/beam pruning, estimation quality 변화가 가져온 SINR cost 로 해석할 수 있습니다.

---

## 4. 네 해석에 대한 검토

사용자 해석:

> AP에서 SNR의 데시벨로 유저를 거르든, UE에서 top-N개의 AP에만 연결하든, 효과는 채널의 숫자가 줄고, 이로 인해 파일럿 수가 줄어서 coherent block 안에 데이터를 담을 공간이 더 확보되어서 그런 결과가 나오는 것으로 보임.

검토:

| 항목 | 판정 | 다듬을 점 |
|---|---|---|
| AP/beam-side SNR threshold 가 active set 을 줄임 | 맞음 | "유저를 거른다"보다 "reported AP-beam candidates 를 줄인다"가 정확 |
| UE-side Top-N AP 가 serving/conflict graph 를 줄임 | 맞음 | Top-N은 channel 자체가 아니라 algorithm이 보는 strong AP feature를 줄이는 것 |
| graph 가 sparse 해지면 coloring 에 필요한 pilot 수가 줄어듦 | 맞음 | 단, graph construction 방식에 따라 chromatic number 가 달라짐 |
| pilot 수가 줄면 data region 이 늘어남 | 맞음 | simulator가 `tau_p_actual`로 prelog를 계산한다는 전제가 필요 |
| 그래서 성능이 좋아짐 | 조건부로 맞음 | SINR 손실이 prelog gain보다 작을 때만 |

발표용으로는 이렇게 말해야 합니다:

> AP-side beam filtering and UE-side Top-N selection are two ways of reducing the effective conflict graph. When this pruning keeps the dominant channels but removes weak links, the graph needs fewer pilots, so the saved pilot overhead becomes data transmission time.

---

## 5. Claim 의 공격 지점과 방어 문장

| 위험 | 왜 위험한가 | 발표에서 쓸 방어 문장 |
|---|---|---|
| "그럼 `tau_p=1` 이 최고냐?" | fewer-is-always-better 로 들리면 바로 나오는 질문 | "No. We need a reduced-but-sufficient active set. Too small a pilot set increases contamination and estimation loss." |
| "pilot count 말고 algorithm 차이 아닌가?" | active set, RF chain, graph, SE evaluator 가 섞여 있음 | "We do not claim pilot count is the only factor. But the measured SE gain closely matches the prelog gain, so pilot overhead is the dominant observed lever." |
| "MatchingBeamFixed 는 왜 Random보다 낮나?" | matching 자체가 우수하다는 claim 의 반례 | "That is exactly why our claim is about adaptive pilot overhead, not matching alone." |
| "TopAP 은 K=40 이후 지는데?" | 우리 아이디어의 한계 | "TopAP is less robust under heavier load. Beam-domain matching keeps tau lower in that regime." |
| "`tau_p_actual` 이 실제 시스템에서 바로 줄어드나?" | 프로토콜이 design budget 전체를 reserve 하면 prelog gain 이 사라짐 | "Our result assumes the scheduler pays the actual number of used orthogonal pilots. If the frame reserves the full design budget regardless, this gain becomes a scheduling-design question." |
| "NMSE 직접 봤나?" | channel estimation 손실을 직접 측정하지 않음 | "Not yet. We use SE/P5 as end-to-end evidence; NMSE is a backup/future diagnostic." |

---

## 6. 발표 Slide 에 넣을 구조

### Slide A — Two paths to the same mechanism

| Path | Selection rule | What becomes sparse | Pilot effect |
|---|---|---|---|
| AP/beam-side | beam-detect SNR, active/moderate beam threshold | AP-beam conflict graph | fewer colors |
| UE-side | Top-N strongest APs | AP-overlap conflict graph | fewer colors |

Caption:

> Different pruning rules, same mechanism: fewer effective conflicts reduce the number of orthogonal pilots needed.

### Slide B — Evidence table

우리 환경에서 4개만 넣는 것을 추천:

| Scheme | Mean SE | Mean `tau_p_actual` | Prelog gain |
|---|---:|---:|---:|
| Random | 5.375 | 14.94 | baseline |
| MJH weighted-count strict | 5.833 | 3.23 | +8.67% |
| MJH beam-resource matching | 5.794 | 4.46 | +7.76% |
| Hybrid#3 | 5.659 | 7.90 | +5.21% |

Caption:

> The SE gain tracks the prelog gain almost one-to-one in the main environment.

### Slide C — Caveat

한 문장만 넣기:

> Pilot reduction helps only while the retained AP/beam set is strong enough; after that point, SINR loss dominates.

---

## 7. 최종 발표 문장

### 가장 좋은 버전

> **The dominant gain comes from right-sizing the active AP/beam set: it sparsifies the conflict graph, reduces the actual pilot count, and converts pilot overhead into data transmission time, as long as the retained channels are strong enough.**

### 한국어 발표 버전

> **핵심 이득은 pilot contamination 을 무조건 더 잘 피한 것이라기보다, 약한 AP/beam link 를 제거해 conflict graph 를 sparse 하게 만들고 실제 pilot 수를 줄여 coherence block 안의 data 전송 비율을 키운 데서 나온다. 단, dominant channel 을 잃을 정도로 줄이면 SINR 손실이 커져 이득이 사라진다.**

### 더 짧은 conclusion

> **Fewer pilots help only when they come from a reduced-but-sufficient active set.**

---

## 8. τ_p sweep 결과 (2026-06-07, sweep 완료)

`experiments/presentation_taup_sweep.py` 가 `tau_p_design ∈ {1,2,3,5,7,9,11,13,15,18,22}` × 100 setups × 10 channel samples 로 종료. Figures: [`figures/sweep_taup_*_final.png`](figures/).

### 8.1 Adaptive 계열의 robustness (★ 발표 핵심)

| Scheme | τ_p_actual 범위 (τ_p_design 1→22) | mean SE 범위 |
|---|---|---|
| Mussbah / MJH weighted-default / weighted-power | 6.84 - 7.06 | 5.61 - 5.76 |
| MJH weighted-count strict | 3.11 - 3.24 | 5.75 - 5.90 |
| MJH beam-resource matching | 4.34 - 4.48 | 5.70 - 5.86 |
| Hybrid#3 (TopAP N=8 adaptive) | 7.75 - 7.98 | 5.58 - 5.73 |

→ **adaptive 계열은 design budget 변화에 거의 영향 받지 않음**. τ_p_actual 이 자동으로 chromatic number 에 수렴.

### 8.2 Fixed 계열에 대한 우리 환경 특이사항

| τ_p_design | Random mean SE | Random P5 SE |
|---:|---:|---:|
| 1 | 5.92 | 1.22 |
| 3 | 5.78 | 1.30 |
| 7 | 5.76 | 1.24 |
| 11 | 5.54 | 1.22 |
| 15 | 5.32 | 1.17 |
| 22 | 5.07 | 1.07 |

→ **fixed 계열도 τ_p_design ↓ 에서 SE ↑**. P5 도 안 무너짐. 즉 우리 환경에서는 **sharp SINR cliff 가 관측되지 않음**.

이유 (해석):

- 우리 setting 의 *antenna richness*: L · N = 200 × 8 = **1600 antennas / 50 UEs = 32×**. spatial multi-user separation 이 contamination 손실을 흡수.
- MJH 의 closed-form SINR (K=30, L=100 → 800/30 = 27×) 환경에서는 cliff 가 보일 가능성 (현재 검증 안 됨).

### 8.3 발표에서의 방어 문장 (sweep 결과 반영)

| 위험 | 방어 문장 |
|---|---|
| "그럼 τ_p=1 이 최고냐?" | "In our antenna-rich environment we do not observe a SINR cliff down to τ_p=1, but this is a property of the L·N >> K regime. In smaller systems (e.g., MJH K=30, L=100 closed-form, classical Mussbah K=10, L=100) the cliff exists; our adaptive schemes auto-land in the safe zone in both regimes." |
| "adaptive 의 의의가 줄지 않나?" | "Adaptive schemes still win on two axes: (i) zero parameter tuning — auto-pick the right τ_p_actual regardless of design budget (Section 8.1 above); (ii) EE — they also reduce active RF chains, where Random/GC do not." |

### 8.4 권장 발표 figure

발표용 추가 figure (`figures/sweep_taup_*_final.png` 중 picking 1-2):

1. **`sweep_taup_avg_se_vs_taup_final.png`**: adaptive 계열 평행선 vs fixed 계열 sloping line — *robustness story*. ★ 발표 핵심 추가 슬라이드.
2. **`sweep_taup_tau_actual_vs_taup_final.png`**: τ_p_actual vs τ_p_design — adaptive 의 *auto-tuning* 직접 보여줌.

---

## 9. 최종 판정

발표 conclusion 으로 사용 가능. 단, 다음 세 가지를 반드시 같이 말해야 합니다.

1. **우리는 "파일럿 수가 작을수록 항상 좋다"고 주장하지 않는다.**
2. **우리는 "dominant AP/beam 은 유지하면서 약한 link 를 제거해 actual pilot overhead 를 줄이는 것이 중요하다"고 주장한다.**
3. **현재 결과에서는 SE gain 이 prelog gain 과 거의 일치하므로, pilot overhead reduction 이 가장 강한 설명이다.**

이렇게 말하면 네 Top-N 아이디어와 동료 weighted-threshold / beam-resource matching 아이디어가 하나의 thesis 아래 자연스럽게 묶입니다.
