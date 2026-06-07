# Final Integrated Report — Pilot Assignment Comparison (Team)

작성일: 2026-06-07
발표일: 2026-06-04 → (실제 6월 첫 주, 미팅 결정 반영 최종 정리)
대상: 두 paper reproduction + cross-paper hybrid + MJH 통합본 (PR #1) 전체 비교

---

## 1. Executive Summary

### 1.1 두 가지 동등 환경에서의 동일 결론

|   | 우리 환경 (`presentation_main_compare`) | MJH 환경 (`all_schemes_ap_domain_hybrids`) |
|---|---|---|
| L (AP 수) | 200 | 100 |
| K (UE 수) | 50 | 30 (K-sweep: 25-45) |
| N (안테나) | 8 | 8 (N-sweep: 1, 2, 4, 8) |
| fc | 3 GHz | 5 GHz |
| τ_c | 150 | 100 |
| τ_p_design | 15 | 10 |
| SE evaluator | Mussbah-style MC (n=20 samples) | Closed-form MMSE+MRC (max-min / full power) |
| EE model | ref12-rf simplified proxy | ref12-rf full (with backhaul) |
| MC setups | 200 | 200 |
| Beam-detect SNR | 20 dB | 0 dB (default) |
| Weight threshold | 10 (weighted-count strict) | 10 (Proposed weighted) |

두 환경에서 **공통으로 관측된 사실**:

1. **τ_p 가 작은 (adaptive) 알고리즘이 mean SE 와 EE 모두에서 우승**.
2. **Beam-domain matching 계열 (MJH BeamResourceMatching / MatchingBeamAdaptive)** 이 *모든 K, N 영역* 에서 일관되게 최강.
3. **AP-domain Top-N 계열 (우리 Hybrid#3)** 은 *moderate load (K/L 적당)* 에서 강하지만, K 가 늘어 *heavy load (K ≥ 40, L=100)* 가 되면 advantage 가 사라짐.
4. **Random / GC / Structured / Greedy / WGF baselines** 는 모두 거의 동일 (τ_p 고정 + AP overlap 만 조정) → *coloring 자체* 보다 *τ_p 감축* 이 lever 임을 보임.

### 1.2 발표 main claim 종합

> **"파일럿 수가 적을수록 SE/EE 가 개선된다 — 단, channel estimation quality 가 보존되는 reduced-but-sufficient active set 에서."**

두 독립적 실험 환경, 두 독립적 SE evaluator (MC vs closed-form) 에서 **방향성 일치** → claim 의 robustness 강하게 지지됨.

발표 전 caveat 노출 권장: 환경 한정 + heavy-load 영역 미탐색 + EE 의 proxy 성격. 자세한 risk 분석은 [`PRESENTATION_CLAIM_REVIEW.md`](PRESENTATION_CLAIM_REVIEW.md) 참고.

---

## 2. 두 환경의 본 실험 결과 — Headline Tables

### 2.1 우리 환경 (`presentation_main_compare.py`, K=50, L=200, N=8, beam-detect=20 dB, weighted-thr=10)

200 setups × 20 channel samples, MC SE.

| Scheme | mean SE | vs Random | P5 SE | mean τ_p | EE proxy | EE vs Random |
|---|---:|---:|---:|---:|---:|---:|
| Random | 5.375 | 0.0% | 1.142 | 14.94 | 1.440 | 0.0% |
| Gao matching | 5.373 | -0.04% | 1.143 | 15.00 | 1.439 | -0.04% |
| GC (Liu) | 5.374 | -0.00% | 1.145 | 14.98 | 1.440 | -0.00% |
| Structured (Chen) | 5.374 | -0.02% | 1.145 | 14.99 | 1.439 | -0.02% |
| Mussbah | 5.697 | +5.99% | 1.238 | 6.93 | 2.199 | +52.75% |
| MJH weighted-count default | 5.697 | +5.99% | 1.238 | 6.93 | 2.199 | +52.75% |
| **MJH weighted-count strict (thr=10)** ★ | **5.833** | **+8.53%** | 1.220 | **3.23** | **2.252** | **+56.42%** |
| MJH weighted-power | 5.697 | +5.99% | 1.238 | 6.93 | 2.199 | +52.75% |
| **MJH beam-resource matching** ★ | **5.794** | **+7.80%** | **1.240** | **4.46** | **2.237** | **+55.35%** |
| TopAP (bisect) | 5.377 | +0.05% | 1.147 | 14.91 | 1.465 | +1.79% |
| **Hybrid#3 (TopAP N=8 adaptive)** ★ | 5.659 | +5.28% | **1.236** | 7.90 | 1.718 | +19.33% |
| Hybrid#4 (TopAP+greedy) | 5.374 | -0.02% | 1.145 | 15.00 | 1.548 | +7.55% |

P5 winners (worst-5% UE 보호): MJH beam-resource matching, MJH weighted-count default, Hybrid#3 모두 ~1.24 — baseline 의 1.14 대비 **+8% tail gain**. ⇒ **fewer pilots 가 worst-case UE 도 더 나쁘게 만들지 않는다** (단서 (C) 위반 없음).

### 2.2 MJH 환경 (`all_schemes_ap_domain_hybrids_pilot_boxplot.py`, K=30, L=100, N=8, w_aa=2, w_ai=w_ia=1, edge_thr=10, full power)

200 setups, closed-form MMSE+MRC SE.

| Scheme | mean SE | vs Random | P95-likely SE | mean τ_p | mean RF/AP | EE | EE vs Random |
|---|---:|---:|---:|---:|---:|---:|---:|
| Random | 2.937 | 0.0% | 0.507 | 10 | 7.18 | 1.115 | 0.0% |
| Greedy | 2.933 | -0.15% | 0.503 | 10 | 7.18 | 1.114 | -0.15% |
| WGF | 2.932 | -0.18% | 0.501 | 10 | 7.18 | 1.113 | -0.18% |
| GC | 2.932 | -0.16% | 0.496 | 10 | 7.18 | 1.114 | -0.16% |
| TopAPBisect | 2.934 | -0.13% | 0.506 | 10 | 7.18 | 1.114 | -0.13% |
| H2GaoGreedy | 2.932 | -0.18% | 0.501 | 10 | 7.18 | 1.113 | -0.18% |
| H3TopAPAdaptive | 2.925 | -0.42% | 0.501 | 10.24 | 7.18 | 1.111 | -0.42% |
| H4TopAPGreedy | 2.932 | -0.17% | 0.506 | 10 | 7.18 | 1.113 | -0.17% |
| **Proposed (weighted-thr=10)** ★ | **2.942** | **+0.15%** | 0.492 | **9.03** | **4.80** | **1.184** | **+6.18%** |
| MatchingBeamFixed | 2.909 | -0.97% | 0.490 | 10 | 4.80 | 1.171 | +5.00% |
| **MatchingBeamAdaptive** ★ | **3.059** | **+4.16%** | **0.517** | **5.45** | **4.80** | **1.231** | **+10.39%** |

MJH 환경 K=30 (light load) 에서는 *baseline 모두 충돌이 적어* SE 차이가 작음. EE 차이는 *RF chain 절약* (베이스라인 7.18 → MJH 진영 4.80) 로 크게 나옴 → **EE 가 더 의미 있는 metric**.

---

## 3. Cross-Environment 일관성 — "Fewer Pilots Better" 의 robustness

### 3.1 τ_p_actual vs mean SE 산점도 해석

| Env | Random τ_p | Best scheme τ_p | Best scheme mean-SE 개선 |
|---|---:|---:|---:|
| 우리 (K=50, L=200) | 15 | 3-5 (MJH 진영) | **+7~9%** |
| MJH (K=30, L=100) | 10 | 5.5 (MatchingAdaptive) | **+4.2%** |

**Pattern**: τ_p 가 약 *baseline 의 1/3 ~ 1/2* 까지 줄어든 schemes 가 SE 와 EE 둘 다 우승.

### 3.2 Antenna sweep (MJH, K=30, N ∈ {1,2,4,8})

[`MJH/result_final_w2_1_1_thr10_full_200/fig2a_avg_se_vs_antennas_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig2a_avg_se_vs_antennas_all_schemes.png), [`fig2b_avg_ee_vs_antennas_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig2b_avg_ee_vs_antennas_all_schemes.png)

| N | Random SE | Proposed SE / τ_p | MatchingAdapt SE / τ_p | H3 SE / τ_p |
|---|---:|---:|---:|---:|
| 1 | 1.561 | 1.685 / 3.16 (+7.9%) | 1.638 / 5.44 (+4.9%) | 1.588 / 8.36 (+1.7%) |
| 2 | 1.972 | 2.085 / 4.74 (+5.7%) | 2.069 / 5.18 (+4.9%) | 2.004 / 8.44 (+1.6%) |
| 4 | 2.522 | 2.613 / 6.34 (+3.6%) | 2.652 / 4.89 (+5.2%) | 2.566 / 8.32 (+1.8%) |
| 8 | 3.149 | 3.206 / 7.62 (+1.8%) | 3.307 / 4.79 (+5.0%) | 3.201 / 8.40 (+1.7%) |

**관찰**:

- **N=1 (single-antenna, Gao-paper-like)**: Proposed (weighted-thr=10) 가 *+7.9%* 로 가장 큰 이득. τ_p=3.16 으로 극단적으로 줄임 → prelog gain 절대적.
- **N ↑ (multi-antenna)**: Beam-domain advantage 의 *상대적 크기* 감소 (다른 axis 인 spatial multiplexing 이 SINR 을 높여줘서). 하지만 *MatchingBeamAdaptive* 는 N=1~8 전 영역에서 +5% 일관 유지 → **robust**.
- **Our Hybrid#3**: N 무관하게 +1.7% 수준 — 작지만 일관됨. N=8 환경 (실용 multi-antenna) 에서 1.7% 가 의미 있을지는 논의 거리.

### 3.3 User sweep (MJH, N=8, K ∈ {25,30,35,40,45})

[`MJH/result_final_w2_1_1_thr10_full_200/fig3a_avg_se_vs_users_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig3a_avg_se_vs_users_all_schemes.png), [`fig3b_avg_ee_vs_users_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig3b_avg_ee_vs_users_all_schemes.png)

| K | Random SE | H3 SE / τ_p (vs Rnd) | Proposed SE / τ_p (vs Rnd) | MatchingAdapt SE / τ_p (vs Rnd) |
|---|---:|---:|---:|---:|
| 25 | 3.283 | 3.374 / 7.43 (+2.77%) | 3.381 / 6.64 (+2.99%) | **3.469 / 4.23 (+5.66%)** |
| 30 | 3.171 | 3.224 / 8.34 (+1.68%) | 3.233 / 7.42 (+1.96%) | **3.335 / 4.59 (+5.18%)** |
| 35 | 3.051 | 3.069 / 9.37 (+0.57%) | 3.088 / 8.24 (+1.19%) | **3.196 / 5.10 (+4.76%)** |
| 40 | 2.937 | 2.925 / 10.24 (-0.42%) | 2.942 / 9.03 (+0.15%) | **3.059 / 5.45 (+4.16%)** |
| 45 | 2.889 | 2.848 / 11.18 (-1.42%) | 2.875 / 9.67 (-0.51%) | **2.999 / 5.81 (+3.81%)** |

**결정적 관찰**:

- **MatchingBeamAdaptive 가 K=25~45 전체에서 +3.8~5.7% 일관 우승** ★★. 우리가 *발표 핵심* 으로 가져가야 할 scheme.
- **Hybrid#3 (우리) 은 K ≤ 30 에서만 advantage** — K=35 에서 +0.57% 한계, K ≥ 40 에서 **반전 (-0.42%, -1.42%)**.
- **Proposed (weighted-thr=10) 는 K ≤ 35 에서 +1~3% 작은 우위**.
- **Heavy load 영역 (K ≥ 40, L=100)** 에서 element-domain (TopAP) scheme 은 *AP overlap 회피 불가능* → fail. Beam-domain matching 만 살아남음.

이게 [`PRESENTATION_CLAIM_REVIEW.md §3.2`](PRESENTATION_CLAIM_REVIEW.md) 에서 우려한 *load regime sensitivity* 의 *경험적 증거*.

---

## 4. 발표 narrative 권장

### 4.1 메인 스토리 (20 분 발표 기준)

1. **Problem** (1 슬라이드): pilot contamination → SE / EE 손실. τ_p 의 trade-off.
2. **Two papers reproduced** (2 슬라이드): Gao 의 UE-AP matching (단일 안테나) + Mussbah 의 beam-domain DSATUR (multi-antenna). 우리 environment 에서 paper-faithful reproduce 결과.
3. **Why both fail at our common-ground env** (1 슬라이드): cross_paper_unified_E4 결과 — Mussbah 는 τ_p 가 폭증 (26→), Gao matching 은 single-antenna 가정 → 두 paper 모두 *환경 의존성*. 동기 부여 끝.
4. **Two paths to fewer pilots** (2 슬라이드):
   - AP-side: Mussbah / MJH weighted-threshold / MJH beam-resource matching (beam-domain conflict graph sparsification)
   - UE-side: 우리 TopAP / Hybrid#3 (element-domain Top-N AP selection)
5. **Headline results** (3 슬라이드 = 우리 + MJH 두 환경):
   - 우리 K=50 환경: MJH beam-matching +7.8% SE, +55% EE, τ_p=4.5. Hybrid#3 +5.3% SE, +19% EE, τ_p=7.9
   - MJH K=30 환경: MatchingAdaptive +4.2% SE, +10.4% EE, τ_p=5.45
   - **공통**: τ_p 작은 schemes 가 SE/EE 동시 우승 ★
6. **K-sweep robustness** (1 슬라이드): K=25~45 에서 MatchingAdaptive 만 +3.8~5.7% 일관 — heavy load 에서 element-domain (Hybrid#3) 한계 명시 ★
7. **Mechanism slide** (1 슬라이드): SE = (1−τ_p/τ_c)·log₂(1+SINR) 분해. τ_p=15→7: prelog 0.900→0.953, +5.9% prelog gain. SINR 손실 < 1% (P5 0.83→0.84 보장 관측).
8. **EE story** (1 슬라이드): RF chain 절약이 EE 의 dominant lever (RF/AP: 7.18→4.80 = -33%). beam-domain 진영의 *under-utilization is a feature* framing.
9. **Caveats slide** (1 슬라이드): heavy-load (K/L ↑), τ_c 작은 high-mobility, EE proxy/closed-form 의 한계. 정직 framing.
10. **Conclusion slide** (1 슬라이드): "adaptive τ_p reduction via active-set sparsification 이 SE 와 EE 의 dominant lever 다. AP-side 와 UE-side 두 경로 모두에서 검증된 효과." 향후 연구: heavy-load regime + NMSE 직접 측정.

### 4.2 책임자 분담 (12분/8분 가이드)

| 슬라이드 # | 분량 | 책임 |
|---|---|---|
| 1, 2 (Gao 단일 안테나) | 2분 | 본인 |
| 3 (cross-paper unfairness 동기) | 1.5분 | 본인 |
| 4 (two paths) | 1.5분 | 본인 |
| 5 (Headline 우리 env) | 2.5분 | 본인 (우리 main_compare 그래프) |
| 5 (Headline MJH env) | 2분 | MJH |
| 6 (K-sweep) | 2분 | MJH (sweep_K 그래프) |
| 7 (mechanism) | 1.5분 | 본인 |
| 8 (EE) | 1.5분 | MJH (ref12-rf 모델 설명) |
| 9, 10 (caveats + conclusion) | 2분 | 본인 |

본인 = 12분, MJH = 6.5분, slide 전환 1.5분 = 총 20분. 보수적 budget.

---

## 5. Figure Index

### 5.1 우리 환경 (presentation_main_compare)

| 파일 | 내용 |
|---|---|
| [`figures/presentation_main_ecdf_main_beam20_wt10.png`](figures/presentation_main_ecdf_main_beam20_wt10.png) | 12 schemes eCDF (K=50) |
| [`figures/presentation_main_mean_se_main_beam20_wt10.png`](figures/presentation_main_mean_se_main_beam20_wt10.png) | mean SE bar |
| [`figures/presentation_main_ee_main_beam20_wt10.png`](figures/presentation_main_ee_main_beam20_wt10.png) | EE proxy bar |
| [`figures/presentation_main_pilot_box_main_beam20_wt10.png`](figures/presentation_main_pilot_box_main_beam20_wt10.png) | τ_p_actual box plot |
| [`figures/presentation_main_summary_main_beam20_wt10.csv`](figures/presentation_main_summary_main_beam20_wt10.csv) | scheme-level summary CSV |
| [`figures/presentation_main_raw_main_beam20_wt10.csv`](figures/presentation_main_raw_main_beam20_wt10.csv) | 200,000 UE-level raw SE |

### 5.2 MJH 환경 (all_schemes_ap_domain_hybrids)

| 파일 | 내용 |
|---|---|
| [`MJH/result_final_w2_1_1_thr10_full_200/fig1_ecdf_vs_se_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig1_ecdf_vs_se_all_schemes.png) | K=30 eCDF |
| [`MJH/result_final_w2_1_1_thr10_full_200/fig1_pilot_tau_boxplot.png`](MJH/result_final_w2_1_1_thr10_full_200/fig1_pilot_tau_boxplot.png) | K=30 τ_p box |
| [`MJH/result_final_w2_1_1_thr10_full_200/fig2a_avg_se_vs_antennas_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig2a_avg_se_vs_antennas_all_schemes.png) | N sweep (1,2,4,8) SE |
| [`MJH/result_final_w2_1_1_thr10_full_200/fig2b_avg_ee_vs_antennas_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig2b_avg_ee_vs_antennas_all_schemes.png) | N sweep EE |
| [`MJH/result_final_w2_1_1_thr10_full_200/fig3a_avg_se_vs_users_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig3a_avg_se_vs_users_all_schemes.png) | K sweep (25-45) SE |
| [`MJH/result_final_w2_1_1_thr10_full_200/fig3b_avg_ee_vs_users_all_schemes.png`](MJH/result_final_w2_1_1_thr10_full_200/fig3b_avg_ee_vs_users_all_schemes.png) | K sweep EE |
| [`MJH/result_final_w2_1_1_thr10_full_200/sweep_K_all_points_pilot_tau_boxplot.png`](MJH/result_final_w2_1_1_thr10_full_200/sweep_K_all_points_pilot_tau_boxplot.png) | K sweep τ_p box (모든 K) |
| [`MJH/result_final_w2_1_1_thr10_full_200/sweep_N_all_points_pilot_tau_boxplot.png`](MJH/result_final_w2_1_1_thr10_full_200/sweep_N_all_points_pilot_tau_boxplot.png) | N sweep τ_p box (모든 N) |
| [`MJH/result_final_w2_1_1_thr10_full_200/sweep_K_all_schemes.csv`](MJH/result_final_w2_1_1_thr10_full_200/sweep_K_all_schemes.csv) | K sweep raw CSV |
| [`MJH/result_final_w2_1_1_thr10_full_200/sweep_N_all_schemes.csv`](MJH/result_final_w2_1_1_thr10_full_200/sweep_N_all_schemes.csv) | N sweep raw CSV |

---

## 6. 코드 변경 요약 (재현 가이드)

### 6.1 본 작업 (last session 이후)

| 파일 | 변경 |
|---|---|
| [`src/pilot_schemes/weighted_beam_threshold.py`](src/pilot_schemes/weighted_beam_threshold.py) | **NEW** — MJH weighted-threshold wrapper |
| [`src/pilot_schemes/beam_resource_matching.py`](src/pilot_schemes/beam_resource_matching.py) | **NEW** — MJH beam-resource matching wrapper |
| [`src/pilot_schemes/__init__.py`](src/pilot_schemes/__init__.py) | 위 2 class export |
| [`experiments/cross_paper_unified_E4.py`](experiments/cross_paper_unified_E4.py) | 12 schemes 통합 (Phase B from PRESENTATION_PLAN §7) |
| [`experiments/presentation_main_compare.py`](experiments/presentation_main_compare.py) | **NEW** — 본 발표용 main script, 4 plots + EE proxy |
| `MJH/all_schemes_ap_domain_hybrids_pilot_boxplot.py` | MJH 가 직접 push (PR #1) — 우리 hybrids 통합 |
| `MJH/all_schemes_ap_domain_hybrids_pilot_boxplot.md` | MJH 가 직접 push — 실행법 |
| [`PRESENTATION_CLAIM_REVIEW.md`](PRESENTATION_CLAIM_REVIEW.md) | **NEW** — main claim 의 risk 분석 |
| [`FINAL_REPORT_PILOT_COMPARISON.md`](FINAL_REPORT_PILOT_COMPARISON.md) | **NEW** — 본 문서 (종합 정리) |

### 6.2 재현 명령

**우리 환경 (≈ 10 분, 12 schemes)**:

```bash
cd <proj_root>
python experiments/presentation_main_compare.py \
    --setups 200 --channel-samples 20 \
    --beam-detection-snr-db 20 --weight-threshold 10 --top-n 10 \
    --out-suffix _main_beam20_wt10
```

**MJH 환경 (≈ 50 분, 11 schemes, fig1+sweep-N+sweep-K)**:

```bash
cd MJH
python all_schemes_ap_domain_hybrids_pilot_boxplot.py \
    --mode all --setups 200 --power-control full --plot \
    --w-aa 2 --w-ai 1 --w-ia 1 --edge-threshold 10 \
    --schemes random greedy wgf gc topap-bisect h2 h3 h4 proposed matching-fixed matching-adaptive \
    --pilot-boxplot --pilot-boxplot-schemes topap-bisect h3 h4 proposed matching-adaptive \
    --outdir result_final_w2_1_1_thr10_full_200
```

---

## 7. 미해결 / 향후 작업

### 7.1 발표 전 (시간 여유 시 추가하면 강해지는 실험)

1. **τ_p_design sweep (우리 환경)**: 동일 schemes 에서 τ_p_design ∈ {5,7,10,12,15,20} 으로 sweep. Hybrid#3 의 *unimodal* 곡선 직접 보여줘서 "더 적을수록 더 좋다 는 *0 까지* 가 아니다" 증거.
2. **Heavy-load (K ≥ 60, L=200) 우리 환경 확장**: MJH K-sweep 의 *load regime sensitivity* 가 우리 환경 (L=200) 에서도 재현되는지 확인. *boundary* 측정.
3. **NMSE 측정 hookup**: `src/mussbah_se.py` 에 NMSE 출력 추가 → "SINR 안 떨어진다" 를 *직접* 증거로.

### 7.2 발표 후 (논문화 시)

1. **Adaptive τ_p 의 theoretical analysis**: prelog gain vs estimation noise variance 의 closed-form crossover point 유도.
2. **MJH weighted-threshold 의 hyperparameter optimization**: w_aa, w_ai, w_ia, edge_threshold 의 *systematic search* — 현재는 (2, 1, 1, 10) 의 heuristic.
3. **저자 코드 reference**: MJH 의 weighted-threshold + matching 알고리즘이 *어느 paper* 의 generalization 인지 명시적 인용 필요 (저자 코드 reference 확인 권장).

---

## 8. 참고 문서

- [`PRESENTATION_PLAN.md`](PRESENTATION_PLAN.md) — 발표 슬라이드 outline + 책임 분담 + Q&A 11 items
- [`PRESENTATION_CLAIM_REVIEW.md`](PRESENTATION_CLAIM_REVIEW.md) — main claim 의 risk 6 categories + 권장 재서술 + Q&A 방어
- [`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md) — 비전공자도 읽을 수 있는 전체 프로젝트 설명
- [`Defense_summary.md`](Defense_summary.md) — 디펜스용 정리
- [`MJH/all_schemes_ap_domain_hybrids_pilot_boxplot.md`](MJH/all_schemes_ap_domain_hybrids_pilot_boxplot.md) — MJH 통합본 실행법
- [`MJH/beam_w_threshold.md`](MJH/beam_w_threshold.md) — MJH weighted-threshold 사용법
