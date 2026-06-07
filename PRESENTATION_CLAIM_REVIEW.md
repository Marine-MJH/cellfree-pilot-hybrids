# 발표 Main Clause 검토 — "Fewer Pilots ⇒ Better SE"

작성일: 2026-06-06
대상: 미팅 결정 conclusion *"파일럿 수가 적을수록 성능이 좋아진다 (단, SINR 너무 떨어지지 않을 정도)"* 의 발표 main claim 으로서의 안전성 검토.

---

## 1. Claim 정리

미팅 결정 사항을 분해하면:

| Element | 내용 |
|---|---|
| **(A) 관찰** | 우리 실험에서 active beam/AP 를 줄여서 τ_p 가 적어진 scheme 이 SE 가 더 높음 |
| **(B) 메커니즘 가설** | SE = (τ_c − τ_p)/τ_c · log₂(1+SINR). τ_p ↓ → prelog ↑ → SE ↑ |
| **(C) 단서** | 단, SINR 이 무너질 정도로 channel estimation 을 망가뜨리면 안 됨 |
| **(D) 두 가지 구현 경로** | (i) AP-side SNR threshold (Mussbah/MJH 의 beam-detect SNR), (ii) UE-side Top-N AP 선택 (우리 TopAP family) |
| **(E) 통합 해석** | (i), (ii) 모두 동일 효과: *active channel 수↓ → conflict graph sparser → chromatic τ_p ↓ → coherence block 안 data 영역↑* |

---

## 2. 실험 증거 — 이 claim 을 지지하는가?

### 2.1 본 발표 핵심 결과 (`presentation_main_compare.py`, 200×20, beam-detect=20 dB, weighted-thr=10)

| Scheme | τ_p_actual | Mean SE | vs Random | EE (proxy) |
|---|---:|---:|---:|---:|
| Random / GC / Structured (τ_p=15 고정) | 15 | ≈ 5.04 | 0% | 1× |
| Mussbah (binary adjacency, β-detect=20) | ~7 | ≈ 5.37 | **+6.5%** | **~2.07×** |
| MJH weighted-count strict (thr=10) | **~4** | ≈ 5.37 | **+6.5%** | ~2.07× |
| MJH **beam-resource matching** | **~5** | ≈ 5.38 | **+6.8%** | **~2.08×** |
| Hybrid#3 (TopAP N=8 adaptive) | **~8** | ≈ 5.32 | **+5.5%** | ~1.62× |
| TopAP bisect (τ_p ≤ 15) | ~15 | ≈ 4.97 | -1.4% | 1.0× |

> (구체 수치는 200×20 run 결과로 업데이트 예정)

**관찰**:

- τ_p ↓ 와 mean SE ↑ 사이에 **양의 상관관계** 가 일관되게 관측됨.
- AP-side(Mussbah/MJH) 경로와 UE-side(Hybrid#3) 경로 모두 동일 방향의 효과를 보임 → claim (D), (E) 부분 empirically 지지.
- TopAP bisect 는 τ_p 가 15 까지 차서 prelog gain 없음 → "τ_p 가 작아야 이득이 난다" 는 *necessity* 도 보임 (반례 보강).

### 2.2 SINR 측면 sanity check

`mussbah_uplink_se` 에서 reported (active+moderate) beam 만 사용해 MMSE estimation + MRC combining. β-detect=20 dB 로 reported set 이 좁아지지만, 우리 K=50, L=200, N=8 환경에서 *충분히 dominant* 한 beam 만 골라내어 SINR 의 큰 손실 없음. P5 (5%-likely) SE 도 baseline 과 비슷한 수준 유지 (Random P5 ~0.83 vs MJH-resource-matching P5 ~0.82).

⇒ **단서 (C) 는 본 환경에서 위반되지 않는다**.

---

## 3. 이론적 일관성 검토

### 3.1 SE = (1 − τ_p/τ_c) · log₂(1 + SINR_eff) 의 두 항 trade-off

| τ_p ↓ 가 미치는 영향 | 부호 |
|---|:---:|
| Prelog (1 − τ_p/τ_c) | **+** |
| Pilot contamination (적은 pilot ⇒ 더 많은 UE 가 같은 pilot 공유 ⇒ SINR ↓) | **−** |
| Estimation MSE (training energy = ρ·τ_p, τ_p ↓ ⇒ MSE ↑ ⇒ SINR ↓) | **−** |

**Main clause 가 성립하는 영역**: positive prelog gain 이 SINR 손실보다 큰 *parameter regime*.

수치 예 (τ_c=150 기준):
- τ_p: 15 → 8 ⇒ prelog: 0.900 → 0.947, 약 **+5.2% relative gain on prelog**
- 동일 channel estimation quality 유지 가능하면 SE ≈ +5%, 우리 관측 +5~7% 와 일치.

**Claim 이 깨지는 영역** (presentation 에서 *명시적으로 짚어야* 하는 caveat):
- τ_c 가 작은 high-mobility 시나리오: τ_p=15 vs 8 차이가 더 큼 (e.g., τ_c=100 → 0.85 vs 0.92, +8.2%) → claim 강해짐 ✓
- τ_c 가 매우 큰 indoor 시나리오 (τ_c=400): 0.96 vs 0.98, **+2%만 이득** → claim 약해짐
- K/L 비율 (load) 이 높으면 same-pilot 충돌 inevitable → SINR 손실이 prelog gain 압도 → **claim 반전 가능**

### 3.2 K, L 의 sensitivity

본 환경: K=50, L=200 (load ratio 0.25). Mussbah paper 환경: K=10, L=100 (0.1). Gao paper: M=200, K=500 (0.4). 우리 결과는 *moderate load* 에서 잘 작동.

**잠재적 반례**: K=200, L=200, N=8 같은 *heavy load* 시 τ_p < log₂(K/L) ≈ 0 → 어떤 algorithm 도 충돌 방지 불가 → "fewer pilots" 가 더 이상 작동 안 함.

발표에서: "moderate load regime (K ≪ L·N) 에서 본 결과" 라고 못 박는 게 안전.

---

## 4. Main Clause 의 잠재 risk 와 대응

### 4.1 위험 요소 정리

| # | 위험 | 본 발표에서의 노출도 | 권장 대응 |
|---|---|---|---|
| R1 | **Confounding**: Mussbah 가 τ_p ↑ 인데도 결과 좋지 않은 게 *"pilot 수 때문"* 인지 *"Mussbah algorithm 이 이 K/L 에서 sub-optimal"* 때문인지 분리 불가 | 중간 | "Mussbah algorithm 자체 수치는 paper 환경에서 작동, 우리 환경에서는 conflict 너무 많아 τ_p ↑" 로 *환경 dependency* 강조 |
| R2 | **단조성 과장**: "더 적을수록 더 좋다" 로 해석되면 τ_p=1 까지 줄여야 한다는 *오해* | 높음 | "single MC 곡선이 *unimodal* 임" 을 sensitivity sweep 으로 보여주거나, 발표문에서 *"a smaller τ_p, when feasible without SINR collapse"* 처럼 조건부 표현 |
| R3 | **General claim vs scenario-specific**: 단일 환경 (K=50, L=200, N=8, τ_c=150) 결과를 *general claim* 으로 oversell | 높음 | 환경 명시 + "we observe within this regime" 로 한정 |
| R4 | **EE 모델의 proxy 성격**: 우리 EE 는 *ref12-rf simplified* 로 활성 RF chain × p_rf + p_fix 만 고려. Backhaul, processing power 누락 | 낮음 | EE plot 의 axis label 에 "(proxy, ref12-rf simplified)" 명시 (이미 plot 에 적용) |
| R5 | **τ_p_actual vs τ_p_design 혼동**: τ_p=15 로 reserve 했지만 실제 사용은 적은 것 — coherence-block 의 *물리적* gain 인지 *reservation* 만 줄인 것인지 | 중간 | "all schemes share τ_p_design=15 budget; only beam/AP-aware ones actually pay τ_p_actual < 15" 로 *budget allocation* 관점 명시 |
| R6 | **Estimation MSE 측정 부재**: 우리 metric 은 SE/EE 뿐, NMSE 직접 보고 안 함 → "SINR 안 떨어진다" 는 결과로 *간접* 추정 | 낮음 | Q&A 대비로 NMSE 그래프 backup slide 준비 권장 |

### 4.2 R1 (Confounding) 더 깊은 분석

Mussbah 가 우리 환경에서 *τ_p_actual ~26* 인 이유: K=50 UEs, beam_detect=0 dB (default) 에서 reported beam 이 매우 많아 → adjacency 매우 dense → DSATUR 가 26 colors 사용. 이건 **algorithm 의 한계** + **environment 의 conflict density** 의 *합작*.

`beam_detect=20 dB` 로 olive 하면 Mussbah 도 τ_p_actual ~7 까지 떨어지고 SE +6.5% → "Mussbah 도 환경 tuning 하면 잘 작동한다" 가 결론.

⇒ **R1 대응**: 발표에서 "beam-detect SNR threshold tuning 으로 Mussbah 자체도 SE 개선" 을 *first finding* 로 제시하면 우리 contribution 의 *시점* 이 명확해짐. 즉:

1. 기존 Mussbah default (β-detect=0) → too many reported beams → τ_p ↑ → SE ↓
2. β-detect 를 늘리거나 weighted threshold 추가 → reported set sparser → τ_p ↓ → SE ↑
3. 같은 방향성을 *UE-side AP selection (TopAP)* 로도 달성 가능 — independent 검증

---

## 5. 권장 main clause 재서술 안

**원안**: *"pilot 수가 적을수록 성능이 좋다"*

**개선안 1 (Conservative)**: *"본 K=50, L=200, N=8, τ_c=150 환경에서, beam-domain 혹은 AP-domain conflict graph 의 sparsification 으로 τ_p_actual 을 줄인 schemes 가 prelog gain 을 통해 mean SE 와 EE 를 동시에 개선함."*

**개선안 2 (Direct, recommended)**: *"Coherence block 내 pilot overhead 를 능동적으로 줄이는 것이 cell-free massive MIMO 에서 핵심 lever 다. AP/UE 어느 한 쪽에서 active set 을 줄이든 효과는 동일 — sparser conflict graph → fewer pilots → larger data prelog."*

**개선안 3 (Critical, defensive)**: *"τ_p adaptive 화는 SE 와 EE 양쪽에서 의미 있는 개선을 제공한다. 단 이 효과는 (i) channel estimation 이 충분한 SINR 을 유지하는 'reduced but sufficient' active set 에서만 성립하며, (ii) load regime (K vs L·N) 이 conflict 를 inherent 하게 만들지 않을 때 한정된다."*

미팅 결정 narrative 와 가장 맞는 안: **개선안 2** (direct + memorable) + **개선안 3 의 caveats** 을 backup slide 로.

---

## 6. 발표 슬라이드 구성 권장 (10-20 분 안에서 안전)

1. **Setup slide**: K=50, L=200, N=8, τ_c=150, β-detect=20 dB, weighted-thr=10 의 *환경 한정* 명시
2. **Headline slide**: 12-scheme eCDF + mean SE bar (현재 작업 결과)
3. **The "fewer pilots" finding**: pilot box plot + τ_p_actual vs mean SE scatter (*correlation visualisation*)
4. **Mechanism slide**: SE = (τ_c-τ_p)/τ_c × log₂(1+SINR) 분해, prelog gain 수치화
5. **Two paths same destination**: AP-side (Mussbah/MJH) vs UE-side (TopAP) 비교 — independent 검증으로 framing
6. **EE slide**: EE proxy bar + caveat (ref12-rf simplified)
7. **Caveat slide** (Q&A 방어용): R2, R3, R5 의 *한계 조건* 명시 ★
8. **Conclusion slide**: 개선안 2 의 main clause + 향후 연구 (heavy-load regime, NMSE 측정 추가)

---

## 7. 검토 결론

미팅 main clause **"파일럿 수가 적을수록 성능이 좋다"** 는 **방향성으로는 적절** 하지만, 다음 조건을 *명시적으로* 짚어야 안전합니다:

- ✅ **본 환경 (K=50, L=200, N=8, τ_c=150, moderate load)** 에서 일관되게 관측됨
- ⚠️ **단조성 표현 주의** — "적을수록"이 "0 까지" 로 해석되지 않게
- ⚠️ **Channel estimation quality 보장** 이 prerequisite — "active set 줄이되 dominant beam 은 살린다"
- ⚠️ **Heavy-load regime** 에서는 claim 반전 가능 — 본 작업의 미해결 boundary
- ✅ **두 경로 (AP-side, UE-side)** 가 같은 결론 — independent corroboration ⇒ claim robustness ↑

➡️ **권장**: 개선안 2 의 main clause + 개선안 3 의 caveat slide. 이로써 reviewer/audience 가 R2, R3 으로 공격할 여지를 사전에 차단.

---

## Appendix A: 본 검토를 강화하는 추가 실험 (시간 여유 시)

1. **τ_p sweep on Hybrid#3** (τ_p ∈ {3, 5, 7, 9, 11, 13, 15}) → "fewer pilots better" 가 *unimodal* 임을 직접 보여주는 곡선. 단조성 R2 risk 완전 해소.
2. **NMSE measurement** (`mussbah_se` 에 NMSE 출력 추가) → SINR 손실 없음을 *직접* 입증, R6 risk 해소.
3. **K sweep** (K ∈ {20, 50, 100, 150, 200}) → heavy-load regime 에서 claim 반전 boundary 측정, R3 risk 해소.

위 3개 중 시간 여유 보고 1개 (τ_p sweep) 만이라도 추가하면 발표 robustness 큰 향상.
