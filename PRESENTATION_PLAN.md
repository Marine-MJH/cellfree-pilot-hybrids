# Presentation Plan — 발표/실험 계획

작성일: 2026-06-05. 최종 갱신: 2026-06-07. 발표시간: **20분 (Q&A 별도)**.

> **🆕 2026-06-07 update**: PR #1 (MJH 통합본) merge 이후 final 실험 + cross-environment 비교 완료. **§5.0 최종 결과** 가 발표 headline numbers — 그 아래 §5.1-§5.6 은 단계별 milestone 보존 (참고용). 종합 정리는 [`FINAL_REPORT_PILOT_COMPARISON.md`](FINAL_REPORT_PILOT_COMPARISON.md), main claim 의 risk 분석은 [`PRESENTATION_CLAIM_REVIEW.md`](PRESENTATION_CLAIM_REVIEW.md).

## 0. 미팅 agenda (먼저 합의할 의사결정 항목)

미팅 시 다음 항목들을 *순서대로* 합의:

1. **§3.1 발표 형식 / 도구**: Beamer vs PowerPoint vs Marp — 한 가지 확정
2. **§3.2 통합 narrative 방향**: "Joint team contribution" vs "각자 separate" — 한 가지 확정
3. **§3.3 추가 실험 범위**: Phase A-D 진행 / Phase A-E / skip — 결정
4. **§4 slide 분담**: 누가 어느 slide 담당 (13 slides)
5. **§9 D-day timeline**: 발표일 + rehearsal 스케줄 합의
6. **§11 Post-presentation**: paper / repo / portfolio 정리 방향

---

## 1. 팀 분담 — 두 사람의 작업 통합

### 1.1 MJH 동료 작업 (`MJH/`)

핵심: **Mussbah paper-faithful 의 *missing pieces 채움*** + 새 algorithm 제안.

| 항목 | 우리 작업 | MJH 작업 | Note |
| --- | --- | --- | --- |
| Mussbah Eq.(10)-(14) closed-form | ✗ Monte-Carlo 대체 | **✓ 정확 구현** | `MJH/beam_w_threshold.py:816-845` 의 `expected_second_moment` + `sinr_closed_form` |
| Mussbah paper Fig.1 의 5 baseline | △ Random + GC (Liu) 만 | **✓ Random + Greedy (Ngo 2017) + WGF (Zeng 2021) + GC (Liu) + Proposed (Mussbah)** | `baseline_assignment` |
| EE metric + RF chain on/off | ✗ | **✓** | paper §IV (RF on/off), §V (EE = Σ SE / P_tot) |
| Mussbah Fig.2 (sweep N) | ✗ | **✓** | `--mode sweep-n` |
| Mussbah Fig.3 (sweep K) | △ paper-faithful 미흡 | **✓** | `--mode sweep-k` |
| 새 algorithm | 4 hybrids (TopAP-based) | **weighted-threshold (beam-domain weighted)** | `--proposed-graph weighted-count/weighted-power` + `--weight-threshold` |

### 1.2 우리 작업 (`src/`, `experiments/`)

핵심: **Gao reproduce + D1/D2 axis diagnostic + 4 TopAP-based hybrids + cross-paper benchmark E1-E4**.

| 항목 | 우리 작업 |
| --- | --- |
| Gao 2024 reproduce (single-antenna paper-faithful) | ✓ 200 MC + bootstrap CI + multi-seed (s=7, 42) |
| Liu/Chen baseline (paper-faithful from MATLAB 코드) | ✓ `src/pilot_schemes/{graph_coloring,structured_access}.py` |
| D1/D2 axis decision-level diagnostic | ✓ `Diagnosis.md §3-§5` |
| TopAP (bisect) — Hybrid #1 | ✓ D1 axis + N-bisection |
| H2 Gao+greedy — Hybrid #2 | ✓ D1 (Gao grouping) + D2 (greedy contam-min) |
| Hybrid#3 (TopAP N=8 adaptive) — *main contribution* | ✓ TopAP graph + Mussbah-style adaptive τ_p |
| Hybrid#4 (TopAP + greedy) | ✓ TopAP graph + D2 greedy |
| Cross-paper benchmark E1/E2/E3/E4 | ✓ multi-antenna unified |
| Statistical defense (bootstrap CI, multi-seed) | ✓ |
| 21 unit tests | ✓ |

### 1.3 통합 narrative (확정 필요 — §3.2)

> "두 사람이 *complementary 한 측면* 을 모두 cover. MJH 는 *Mussbah paper-faithful reproduce
> 의 missing pieces (closed-form Eq.10-14, Greedy/WGF baseline, EE metric)* 및 새
> weighted-threshold algorithm. 본인은 *Gao reproduce, D1/D2 diagnostic, 4 TopAP
> hybrids, cross-paper E1-E4 benchmark*. 합쳐서 **두 paper 의 full faithful reproduce
> 및 5가지 new algorithms 및 cross-paper unified benchmark**."

---

## 2. 메인 message 결정

발표의 *single most important sentence*:

> **"Gao 와 Mussbah 두 paper 를 paper-faithful 하게 재현했고, 두 알고리즘이 보는 conflict
> 구조의 차이를 D1/D2 axis diagnostic 으로 분석했으며, 그 결과로 만든 Hybrid#3 (sparse
> element-domain conflict + adaptive τ_p) 가 common-ground benchmark E4 에서 평균 SE
> +5.31% 의 statistically significant 우위를 보였다."**

이 한 문장이 *모든 slide 의 throughline*. Slide 12 (Conclusion) 의 마지막 줄에 그대로 사용.

---

## 3. 의사결정 항목 (미팅에서 합의)

### 3.1 발표 형식 / 도구

| Option | 장점 | 단점 | 추천 |
| --- | --- | --- | --- |
| **LaTeX Beamer** | 수식 polish, version control | 컴파일 시간, 학습 비용 | 학술 발표 정석. paper-style 수식 많음 → ★ |
| **PowerPoint / Keynote** | visual polish, transition | 수식 입력 번거로움, 공동작업 어려움 | 발표 사진 / 다이어그램 중심이면 OK |
| **Marp** (Markdown → slide) | 빠른 prototyping, git 친화 | visual customization 제한 | 시간 부족 시 |

**추천**: Beamer (academic standard). 본인 / MJH 가 LaTeX 능숙도에 따라 결정.

### 3.2 통합 narrative 방향

| Option | 시나리오 | Slide 분담 |
| --- | --- | --- |
| **Option A: Joint contribution** | 두 사람이 *팀 work* 으로 발표. 각자 slide 책임 분담 but message 통합. | §4 의 책임자 column 적용 |
| **Option B: Separate** | 두 사람 각자 독립 발표 (10분씩) | 각자 separate plan |

**추천**: Option A — *sum > parts*. MJH 의 closed-form + 우리 cross-paper E4 가 시너지 강함.
교수님 입장에서 *팀 work narrative 가 evaluation 우호적*.

### 3.3 추가 실험 범위

§7 의 5 phase 중 어디까지:

| Scope | 시간 | 결과물 | 발표 추가 가치 |
| --- | --- | --- | --- |
| **Skip** | 0시간 | 현재 결과만 | 12 slides, MJH 결과 standalone 인용 |
| **A+B+C+D (최소)** | 3시간 | Cross-family E4 figure (12 schemes) | Slide 9.5 추가 → 13 slides ★ |
| **A+B+C+D+E** | +1시간 | + sensitivity sweep | Q10/Q11 답변 강화 |
| **+ Hybrid#5 prototype** | +1시간 | + TopAP + weighted 결합 | "향후 작업" 가 *currently working* 으로 격상 |

**추천**: A+B+C+D (3시간) — *통합 narrative 의 정수* (slide 9.5). E 와 Hybrid#5 는 시간 여유 보고.

### 3.4 발표 시점 / rehearsal

- 발표일: ?? (미팅에서 확인)
- 1차 rehearsal: 발표일 -3일
- Final rehearsal: 발표일 -1일
- Slide draft 완성: 발표일 -5일

---

## 4. Slide outline (20분, 13 slides)

| # | Title | 시간 | 책임자 | Main figure / claim |
| --- | --- | ---: | --- | --- |
| 1 | Title + 팀 contribution | 1.0 | 양쪽 | 팀명 + 한 줄 message |
| 2 | System model + pilot contamination | 1.5 | A | Cell-free MIMO diagram + 수식 |
| 3 | Two papers + cross-paper difficulty | 1.5 | A | Gao N=1 vs Mussbah N=8 table |
| 4 | Gao reproduce | 2.0 | 우리 | `gao_fig3_vs_pilot_number_final200.png` + "+21.7% vs paper +23%" |
| 5 | Mussbah paper-faithful reproduce | 2.0 | MJH | MJH eCDF + closed-form Eq.10-14 + 5 baselines |
| 6 | D1/D2 axis diagnostic | 1.5 | 우리 | D1/D2 table (Diagnosis §4) |
| 7 | 5 new algorithms 구조 | 1.5 | 양쪽 | Algorithm × D1/D2/adaptive matrix |
| 8 | Cross-paper benchmark E1-E4 | 1.5 | 우리 | E1-E4 환경 table |
| 9 | E4 headline (Hybrid#3 +5.31%) | 2.0 | 우리 | `cross_paper_unified_3env.png` + bootstrap CI |
| 9.5 | Cross-family head-to-head (TopAP vs weighted-threshold) | 2.0 | 양쪽 | 새 figure (§7 작업 결과) |
| 10 | Mechanism — actual pilot count | 1.5 | 우리 | `cross_paper_unified_E4_tau_p_actual.png` + training overhead 분해 |
| 11 | Honest limitations | 1.0 | 양쪽 | Mussbah +8% 미재현 / E4 paper reproduce 아님 / K-sensitivity |
| 12 | Conclusion + 한 줄 message | 0.5 | 양쪽 | §2 의 main sentence |
| **Total** | | **20.0** | | |

⚠️ Slide 9.5 는 §3.3 의 추가 실험 결정에 따라 *포함/제외*. Skip 시 12 slides (시간 여유 +2분).

### 4.1 Slide 별 책임자 가이드

- **A**: 양쪽 합의 — 미팅에서 결정
- **우리**: 본인 발표
- **MJH**: MJH 동료 발표
- **양쪽**: 교대 또는 합의

권장: *발표자 잦은 transition* 보다 *한 사람이 큰 block 책임* — 청중 attention 유지.

권장 분담:

- **본인 (12분)**: Slide 1 (intro 절반) + 4 + 6 + 7 (절반) + 8 + 9 + 10 + 12 (절반)
- **MJH (8분)**: Slide 2 + 3 + 5 + 7 (절반) + 11
- Slide 9.5: 본인+MJH 교대 (각자 algorithm family 설명)

---

## 5. Headline numbers — 외울 정확한 숫자들

발표 중 *정확히 인용* 할 수치. **§5.0 이 final, §5.1-§5.6 은 historical milestone**.

### 5.0 ★ 최종 결과 (2026-06-07, 12 schemes, beam-detect=20 dB, weight-thr=10)

#### 5.0.A 우리 환경 — K=50, L=200, N=8, fc=3 GHz, τ_c=150, 200 setups × 20 ch

[`experiments/presentation_main_compare.py`](experiments/presentation_main_compare.py) — Mussbah-style MC SE.

| Scheme | Mean SE | vs Random | P5 SE | Mean τ_p | EE proxy | EE vs Random |
|---|---:|---:|---:|---:|---:|---:|
| Random / GC / Structured / Gao matching | ≈ 5.374 | 0% | 1.14 | 15.0 | 1.44 | 0% |
| Mussbah / MJH weighted-count default / MJH weighted-power | 5.697 | **+5.99%** | 1.238 | 6.93 | 2.199 | **+52.75%** |
| **MJH weighted-count strict (thr=10)** ★ | **5.833** | **+8.53%** | 1.220 | **3.23** | **2.252** | **+56.42%** |
| **MJH beam-resource matching** ★ | **5.794** | **+7.80%** | **1.240** | **4.46** | 2.237 | **+55.35%** |
| **Hybrid#3 (우리)** ★ | **5.659** | **+5.28%** | **1.236** | **7.90** | 1.718 | +19.33% |

#### 5.0.B MJH 환경 — K=30, L=100, N=8, fc=5 GHz, τ_c=100, 200 setups, full power, closed-form SINR

[`MJH/all_schemes_ap_domain_hybrids_pilot_boxplot.py`](MJH/all_schemes_ap_domain_hybrids_pilot_boxplot.py) — w_aa=2, w_ai=w_ia=1, edge_thr=10.

| Scheme | Mean SE | vs Random | Mean τ_p | EE | EE vs Random |
|---|---:|---:|---:|---:|---:|
| Random / baselines | ≈ 2.937 | 0% | 10.0 | 1.115 | 0% |
| **MatchingBeamAdaptive** ★ | **3.059** | **+4.16%** | **5.45** | **1.231** | **+10.39%** |
| Proposed (weighted-thr=10) | 2.942 | +0.15% | 9.03 | 1.184 | +6.18% |
| Hybrid#3 (우리, K=30) | 2.925 | -0.42% | 10.24 | 1.111 | -0.42% |

#### 5.0.C K-sweep load-regime boundary (MJH env, K=25..45)

| K | Hybrid#3 vs Random | Proposed vs Random | MatchingBeamAdaptive vs Random |
|---:|---:|---:|---:|
| 25 | +2.77% | +2.99% | **+5.66%** |
| 30 | +1.68% | +1.96% | **+5.18%** |
| 35 | +0.57% | +1.19% | **+4.76%** |
| 40 | **-0.42%** ★ | +0.15% | **+4.16%** |
| 45 | **-1.42%** ★ | -0.51% | **+3.81%** |

★ = **Heavy-load (K ≥ 40) 에서 Hybrid#3 (element-domain) advantage 반전**. Beam-domain matching adaptive 만 robust → 발표 caveat 슬라이드 핵심 증거.

#### 5.0.D 메인 message (final)

> **"두 독립 환경 + 두 독립 SE evaluator (MC vs closed-form) 에서 일관되게: adaptive τ_p reduction 이 SE 와 EE 양쪽의 dominant lever. AP-domain (Mussbah / MJH weighted-threshold / beam-resource matching) 과 element-domain (우리 TopAP / Hybrid#3) 모두 같은 방향. 가장 robust 한 single scheme 은 *MJH beam-resource matching (adaptive)* — K=25~45 전체에서 +3.8~7.8% SE 일관."**

### 5.1 Gao reproduce

- τ_p=10, max-min power, Gao vs Random: **+21.7%** (paper claim +23%)
- 200 Monte Carlo setups, bootstrap CI 의 3.0× margin 위
- Multi-seed (s=7, s=42) 차이 < 3%

### 5.2 Mussbah reproduce

- Default τ_p=10, K=30: 우리 +1.6% (paper claim +8%) — *literal default 미재현*
- SNR +6dB threshold reinterpretation: chromatic 12 → 8, Mussbah +2.3%
- τ_p=20 envelope: Mussbah +12.4%, **Hybrid#3 +14.0%** vs Random
- K-sweep (paper Fig.3 envelope):
  - K=25: Hybrid#3 +5.8%, Mussbah +2.6%
  - K=35: Hybrid#3 +7.1%, Mussbah +1.0%
  - K=45: Hybrid#3 -3.5%, Mussbah -5.1%

### 5.3 E4 unified benchmark (★ 메인 결과)

E4 setting: K=50, M=200, N=8, 3 GHz, τ_c=150, τ_p_design=15, UMi + one-ring + Rician.
200 setups × 20 channel samples.

| Scheme | P5 SE | Mean SE | vs Random | Mean actual τ_p | Bootstrap 95% CI |
| --- | ---: | ---: | ---: | ---: | --- |
| **Hybrid#3** | **1.234** | **5.572** | **+5.31%** ★ | **7.90** | [5.515, 5.627] |
| Random | 1.149 | 5.291 | — | 14.94 | [5.237, 5.347] |
| TopAP (bisect) | 1.159 | 5.295 | +0.08% | 14.91 | (overlap with Random) |
| H2 Gao+greedy | 1.162 | 5.291 | +0.01% | 15.00 | (overlap) |
| Hybrid#4 | 1.161 | 5.292 | +0.01% | 15.00 | (overlap) |
| GC (Liu) | 1.169 | 5.292 | +0.02% | 14.98 | (overlap) |
| Structured (Chen) | 1.162 | 5.292 | +0.01% | 14.99 | (overlap) |
| Gao matching | 1.153 | 5.290 | -0.01% | 15.00 | (overlap) |
| **Mussbah** | **1.059** | **4.845** | **-8.44%** | **26.52** | [4.794, 4.898] |

### 5.4 Mechanism (actual pilot count 분해)

Training overhead factor `(τ_c - τ_p_actual) / τ_c` (τ_c=150):

- Hybrid#3: (150-7.9)/150 = **0.947** (95% data time)
- Random / others: (150-15)/150 = **0.900** (90% data time)
- Mussbah: (150-26.5)/150 = **0.823** (82% data time)

Ratio:

- Hybrid#3 / Random prefactor = 0.947 / 0.900 = **1.052** → +5.2% SE prefactor
- 우리 측정 +5.31% — *훌륭한 일치*
- Mussbah / Random prefactor = 0.823 / 0.900 = **0.914** → -8.6% SE prefactor
- 우리 측정 -8.44% — *역시 일치*

### 5.5 Seed42 sanity (50 setups × 10 ch)

- Hybrid#3 vs Random: **+5.30%** (main +5.31% 와 거의 정확 일치)
- Mussbah vs Random: -8.12% (main -8.44% 와 비슷)

### 5.6 Statistical metadata

- 21 unit tests pass
- 200 setups (main MC) + 50 setups (seed42 sanity)
- Bootstrap CI: B=1000 resamples
- 모든 algorithm `seed=7` default + seed sweep s=42 verification

---

## 6. 핵심 figures (slides 에 들어갈 5개)

| # | Figure | Slide | 목적 |
| --- | --- | --- | --- |
| 1 | `figures/gao_fig3_vs_pilot_number_final200.png` | 4 | Gao reproduce — small-τ_p +21.7% |
| 2 | MJH eCDF figure (예: `MJH/test_figure_test/fig1_*.png`) | 5 | Mussbah paper-faithful Fig.1 |
| 3 | D1/D2 table (rendered from `Diagnosis.md §4`) | 6 | Diagnostic motivation |
| 4 | `figures/cross_paper_unified_3env.png` | 9 | E2/E3/E4 비교, headline |
| 5 | `figures/cross_paper_unified_E4_tau_p_actual.png` | 10 | Mechanism — actual pilot count |

### 6.1 Backup figures (Q&A 대비)

| Figure | 어떤 질문에 사용 |
| --- | --- |
| `figures/envelope_tau_p_K30.png` | Q: Mussbah advantage 의 enabling condition |
| `figures/envelope_advantage_vs_random.png` | Q: Mussbah K-sensitivity |
| `figures/cross_paper_unified_E4_cdf_E4.png` | Q: distribution shape |
| `figures/cross_paper_unified_E4_effect_decomposition.png` | Q: actual pilot 분해 |
| `figures/two_by_two_gao_mussbah_matrix.png` | Q: cross-paper 의 강제 transplant |

### 6.2 새 figure (추가 실험 시, §7)

| Figure | Slide 9.5 |
| --- | --- |
| `figures/cross_paper_unified_E4_cross_family.png` | TopAP family (4) vs weighted-threshold family (3) + baselines (4) bar chart |
| `figures/cross_paper_unified_E4_cross_family_actual_tau_p.png` | actual τ_p per scheme (12) |
| `figures/weighted_threshold_sensitivity.png` (optional Phase E) | (w_aa, w_am, threshold) sweep |

---

## 7. 추가 실험 plan — Top-N vs k-threshold cross-family

### 7.1 Phase A — MJH algorithm 을 우리 framework 으로 wrap (1시간)

새 파일 `src/pilot_schemes/weighted_beam_threshold.py`:

```python
class WeightedBeamThresholdPilotAssignment(PilotAssignmentScheme):
    """MJH's weighted-threshold beam-domain pilot assignment.

    Generalisation of Mussbah Algorithm 1:
    W[i,j] = w_aa · Baa[i,j] + w_am · (Bai[i,j] + Bia[i,j])
    Adjacency = W > threshold; DSATUR coloring.
    (w_aa=w_am=1, threshold=0) recovers original Mussbah binary.
    """
    name = "Weighted-Threshold"

    def __init__(self, seed, delta=0.95, w_aa=2.0, w_am=1.0, threshold=0.0,
                 variant="weighted-count", adaptive_tau_p=True):
        ...

    def assign(self, network, tau_p):
        b_active, b_inactive = network.beam_info(delta=self.delta)
        if self.variant == "weighted-count":
            Baa = b_active.T @ b_active
            Bai = b_active.T @ b_inactive
            Bia = b_inactive.T @ b_active
            W = self.w_aa * Baa + self.w_am * (Bai + Bia)
        elif self.variant == "weighted-power":
            # Use network.beam_powers for sqrt(power) weighting
            ...
        adjacency = (W > self.threshold)
        colors = dsatur_coloring(adjacency)
        # adaptive or modulo
```

DSATUR coloring 함수는 `beam_domain_mussbah.py:_dsatur_coloring` 재사용.
Smoke test 1개 + unit test 1-2개.

### 7.2 Phase B — E4 build_schemes 에 추가 (30분)

`experiments/cross_paper_unified_E4.py` 의 build_schemes 에 3 variants:

| Variant | Config | 의미 |
| --- | --- | --- |
| `Weighted-count default` | `w_aa=2, w_am=1, threshold=0, adaptive=True` | MJH 기본 |
| `Weighted-count strict` | `w_aa=2, w_am=1, threshold=3, adaptive=True` | weak conflict 제거 |
| `Weighted-power` | `w_aa=2, w_am=1, threshold=0, variant=power, adaptive=True` | MJH power-weighted |

총 12 schemes (기존 9 + 3).

### 7.3 Phase C — 200×20 MC background run (~1.5시간)

```bash
nohup python experiments/cross_paper_unified_E4.py \
    --setups 200 --channel-samples 20 \
    --out-suffix _E4_with_weighted \
    > logs/E4_weighted.log 2>&1 &
```

200 × 20 × 12 = 48k SE evaluations. 1-1.5시간 wall clock.

### 7.4 Phase D — Figures + bootstrap CI (1시간)

1. **`figures/cross_paper_unified_E4_cross_family.png`**:
   - Group 1 (회색): Random, Gao matching, GC, Structured
   - Group 2 (주황): Mussbah, Weighted-count default, Weighted-count strict, Weighted-power
   - Group 3 (보라/분홍): TopAP bisect, H2, Hybrid#3, Hybrid#4
2. **`figures/cross_paper_unified_E4_cross_family_actual_tau_p.png`**: 12 schemes 의 actual τ_p
3. Bootstrap CI:

   ```bash
   python experiments/bootstrap_se_ci.py \
       --input cross_paper_unified_E4_raw_E4_with_weighted.csv
   ```

### 7.5 Phase E (optional, +1시간) — Sensitivity sweep

weighted-threshold 의 sweet spot 식별:

- threshold ∈ {0, 1, 3, 5, 10}
- (w_aa, w_am) ∈ {(2,1), (2,0.5), (3,1), (1,1)}

새 figure `figures/weighted_threshold_sensitivity.png` — Q&A 강화용.

### 7.6 총 시간 추정

| Phase | 시간 |
| --- | --- |
| A: Wrapper | 1.0 |
| B: build_schemes | 0.5 |
| C: MC run (background) | 1.5 |
| D: Figures + CI | 1.0 |
| E (optional): Sensitivity | +1.0 |
| **Total (without E)** | **4.0** |
| **Total (with E)** | **5.0** |

---

## 8. Q&A 준비 (11개)

### Q1. Gao 가 모든 setting 에서 최고가 아닌 이유?

Liu/Chen baseline 을 *원저자 MATLAB 코드 기반 paper-faithful 구현*. Gao paper 의 reference
구현보다 우리 Liu/Chen 이 강함. *Small-τ_p* 영역에서만 Gao 우위 (paper §V 도 small-τ_p
강조). PROGRESS.md §3.1.

### Q2. Mussbah paper +8% default 조건 미재현?

Paper §II spec 모두 구현 (3GPP UMi + one-ring + Rician + Eq.10-14 closed-form by MJH).
우리 환경 chromatic ≈ 12 > τ_p_design = 10 → Mussbah modulo wrap → adaptive τ_p advantage
사라짐. SNR +6dB reinterpretation → chromatic 8 → +2.3% (paper +8% 의 training overhead
portion). 나머지는 paper 미명시 micro-detail (DFT codebook, MMSE full covariance) cumulative.
Mussbah_reproduce_plan.md §18.

### Q3. E4 environment 가 자의적인가?

두 paper system model 차이 (N=1 vs N=8) → fair 비교 위해 *common ground 필요*. E4 spec
(K=50, M=200, N=8, 3 GHz) = paper 중간값. Paper reproduction 이 아니라 *common-ground
algorithm benchmark*. 의도적 trade-off.

### Q4. Hybrid#3 의 K-sensitivity 가 weakness 아닌가?

맞음. 우리 4 hybrid 가 *서로 다른 K-envelope 에서 best*. K=50 sweet spot 에서 Hybrid#3,
K=200 stress test 에서 TopAP bisect / H2 / Hybrid#4. *Complementary coverage*. Honest
assessment.

### Q5. Mussbah -8.44% catastrophic 한가?

Mechanism 직접 정량: Mussbah actual τ_p = 26.5 (τ_p_design 15 의 1.77x) → training overhead
factor 0.823 vs Random 0.900 → ratio 0.914 → -8.6% prefactor. 우리 측정 -8.44% 정확 일치.
즉 -8.44% = *우리 unified environment 에서 Mussbah chromatic 폭발의 자연스러운 결과*.
Mussbah algorithm 자체의 잘못 X.

### Q6. MJH weighted-threshold 도 같이 비교했나?

(추가 실험 §7 진행 시) Yes — Slide 9.5 의 `cross_paper_unified_E4_cross_family.png`. E4
환경에서 MJH variant 3개도 같이 평가. Top-N family (우리) vs Weighted-threshold family
(MJH) head-to-head.

### Q7. Statistical confidence 수준?

Bootstrap 95% CI (B=1000) on 200 setups × 20 channel samples. *Mean SE* 에서 Hybrid#3 vs
Random CI 완전 분리 (5.572 [5.515, 5.627] vs 5.291 [5.237, 5.347]). Mussbah vs Random 도
완전 분리. Seed42 sanity (50 × 10) 에서도 +5.30% / -8.12% — seed-robust.

### Q8. Code reproducibility?

21 unit tests pass (`tests/`) — algorithm correctness sanity check. Deterministic seed.
모든 experiment script `experiments/` + README.md / TUTORIAL.md. MJH 작업은 `MJH/`
standalone.

### Q9. 향후 작업?

- (Phase E 진행 시) MJH weighted-threshold sensitivity sweep
- DFT codebook over-complete + MMSE full covariance 로 Mussbah +8% 추가 재현 시도 (1-2일)
- Hybrid#5 candidate: TopAP graph + MJH weighted weighting + adaptive τ_p (1일)
- Multi-seed verification 보강 (1일)
- 학회 paper / 졸업 thesis 활용

### Q10. MJH weighted-threshold 가 Mussbah 보다 좋은가? (추가 실험 진행 시)

E4 환경에서 MJH variant 3개 모두 Mussbah binary 보다 약간 우위 (threshold 로 weak conflict
제거 → fewer pilots, less training overhead). 하지만 우리 Hybrid#3 (TopAP + adaptive) 보다
약함 — *element-domain top-N conflict 가 beam-domain weighted 보다 우리 환경에서 더
sparse*. 자세히 cross-family figure.

### Q11. 우리 hybrid 와 MJH weighted-threshold 결합 가능?

가능. TopAP element-domain conflict graph + MJH weighted active-moderate weighting +
adaptive τ_p = Hybrid#5 candidate. Phase D 완료 후 추가 1시간 작업으로 prototype 가능.

---

## 9. D-day checklist

발표일 -7일:

- ☐ 미팅 합의 사항 확정 (§3 항목들)
- ☐ Slide deck draft 0.5 완성 (text only, figure placeholder)
- ☐ 추가 실험 §3.3 결정 시 Phase A 시작

발표일 -5일:

- ☐ Slide deck draft 1.0 (figures + text)
- ☐ (추가 실험 시) Phase A-D 완료
- ☐ MJH 동료와 분담 협의 완료

발표일 -3일:

- ☐ Slide deck final 0.9
- ☐ 1차 rehearsal (20분 timing 확인)
- ☐ Q&A 11개 답변 외우기 시작

발표일 -1일:

- ☐ Final slide deck (zero errors)
- ☐ Final rehearsal (timing + Q&A 시뮬레이션)
- ☐ Backup figures USB 또는 cloud 백업

발표일 D-day:

- ☐ Headline numbers 마지막 확인 (§5)
- ☐ 발표 전 5분 *§2 의 한 줄 message* 외우기

발표 후:

- ☐ Q&A 결과 노트 (개선 점)
- ☐ Repo 정리 (`cellfree-pilot-hybrids` 추천)

---

## 10. Backup material (Q&A 대비)

### 10.1 Backup slides (slide deck 끝에 hidden)

발표 본문 12-13 slides 외 backup 5개:

| Backup # | 내용 | 어떤 질문에 |
| --- | --- | --- |
| B1 | τ_p envelope figure (`envelope_tau_p_K30.png`) | Q: Mussbah advantage enabling condition |
| B2 | K-sweep advantage figure (`envelope_advantage_vs_random.png`) | Q: K-sensitivity 상세 |
| B3 | 2×2 transplant matrix (`two_by_two_gao_mussbah_matrix.png`) | Q: cross-paper transplant 결과 |
| B4 | Diagnose algorithm D5 metric (decision disagreement) | Q: hybrid space 존재 증명 |
| B5 | Weighted-threshold sensitivity (Phase E 진행 시) | Q: MJH algorithm tunability |

### 10.2 Backup numbers table (외우기)

발표 중 *기억 안 나면 backup slide 보기*:

- 우리 K-sweep 의 모든 K-value 별 P5/Mean (`figures/mussbah_fig3_k_sweep_summary_100x10_v3.csv`)
- E4 의 9 schemes summary (`cross_paper_unified_E4_summary_E4.csv`)
- Bootstrap CI 의 모든 scheme/metric (`bootstrap_ci_unified_E4.csv`)

---

## 11. 미팅 후 next steps

### 11.1 미팅 합의 즉시

- 의사결정 사항 (§3) PRESENTATION_PLAN.md 다시 업데이트
- (Option A 합의 시) Phase A 시작
- Slide deck repository 초기화 (LaTeX project or Marp markdown)

### 11.2 발표 후

- **코드 git repository**: `cellfree-pilot-hybrids` 추천 (이전 추천)
- **Joint paper / report**: 학회 paper 또는 졸업 thesis 활용 가능성
- **MJH 동료와 분리**: 각자 portfolio 에 해당 부분 활용

### 11.3 발표 결과 평가 항목 (self-evaluation)

- ☐ Headline +5.31% 가 청중에게 정확히 전달됐는가
- ☐ E1-E4 환경 구분 설명이 *fairness narrative* 로 들렸는가
- ☐ Honest limitations slide 가 *defendability* 보여줬는가
- ☐ MJH 와의 *팀 work 통합* 이 자연스러웠는가
- ☐ Q&A 11개 중 몇 개 직접 답변, 몇 개 backup slide 의존

---

## 12. 최종 한 줄 message (Slide 12 마지막 줄)

> "두 paper 의 알고리즘이 보는 *conflict 구조의 차이* 를 D1/D2 axis 로 분리해 진단했고,
> 그 결과로 만든 Hybrid#3 (sparse element-domain conflict + adaptive τ_p) 가 common-ground
> benchmark E4 에서 *statistically significant* 평균 SE +5.31% 의 우위를 보였다."

---

## 부록 — 빠른 참조

| 문서 | 역할 |
| --- | --- |
| `PRESENTATION_PLAN.md` (이 문서) | 발표/실험 계획 + 미팅 의사결정 |
| `PROJECT_EXPLAINED.md` | 초보자도 한 번 읽고 이해하는 전체 설명 |
| `Defense_summary.md` | 1-page defense + FAQ (간략 version) |
| `TUTORIAL.md` | 코드/실험 직접 따라하는 step-by-step |
| `README.md` | Project entry point |
| `PROGRESS.md` | Gao reproduce + cross-paper status |
| `Mussbah_reproduce_plan.md` | Mussbah reproduce 전체 기록 (§1-§22) |
| `Diagnosis.md` | D1/D2 axis diagnostic + hybrid motivation |
| `NEXT_STEPS_AGENT_PLAN.md` | E4 unified benchmark 완료 기록 (다음 agent 참조용) |

**미팅 시 가져갈 문서**: 이 문서 + `Defense_summary.md` (요약) + `PROJECT_EXPLAINED.md` (전체 그림).
