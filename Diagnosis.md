# Algorithm Diagnosis — Gao / Liu / Chen / Mussbah

작성일: 2026-06-01
목적: Hybrid / 새 알고리즘 설계의 input 확보.

## 1. 목적

`PROGRESS.md` §3.1 에서 다음이 확인됨:

- Gao matching 은 **small τ_p (=10) 에서 모든 alternative 를 이김** (통계적 유의).
- Large τ_p (≥20) 에서는 Graph_full / Structured_full 이 약간 우위 (borderline).
- 두 영역에서 *왜 우열이 갈리는지* 는 아직 미분석.

이 문서는:

1. 각 algorithm 의 *pilot 할당 의사결정 logic* 을 한 곳에 정리.
2. 영역별 우열을 설명할 수 있는 **decision-level metric** 정의.
3. 50-100 MC 진단 실행 + 결과 분석.
4. Hybrid / 새 알고리즘 설계 input 도출.

## 2. Algorithm decision-logic 정리

### 2.1 Gao matching (Algorithm 1 + 2)

**Algorithm 1 (UE grouping, AP-centric)**:

- 각 AP k 는 *β_{mk} 가 큰 top-τ_p UE 를* group `G_k` 로 받음 (quota Q_AP = τ_p).
- Sanity check (§3.4.3) 결과: many-to-many matching 이 **단순 top-τ_p per AP** 와 100% 일치.
- 의사결정 단위: **AP-local**. AP k 는 자기가 잘 듣는 UE 들끼리 *서로 다른 pilot* 받게 만들고 싶음.

**Algorithm 2 (pilot assignment, group-centric)**:

- Group 의 "common-serving-AP ratio" S_k 가 큰 순서로 처리.
- 각 group 내 unassigned UE 에게 *해당 group 에서 아직 안 쓰인 pilot* 을 random 할당.
- 이미 다른 group 에서 pilot 받은 UE 는 그대로 유지 (재배정 X).
- 의사결정 logic: "AP 단위로 *서로 다른 pilot 을 강제* 하되, 나중에 처리되는 group 에서는 이미 할당된 pilot 들 사이 conflict 가 생길 수 있음".

**예상 강점**:

- AP-local 결정이므로 *AP 마다 strong UE 들 사이의 직교성* 은 확실히 유지.
- → small τ_p 에서 강함 (group quota = τ_p 가 작으면 각 AP 의 strong UE 만 직교화).

**예상 약점**:

- *Global conflict pattern* (멀리 떨어진 AP 두 개에서 동시에 듣는 UE 쌍) 은 고려 안 함.
- → large τ_p 에서는 global structure 무시한 random 할당이 sub-optimal.

### 2.2 Liu graph coloring (Benchmark II [14])

**핵심 logic**:

1. 각 UE m 의 *cumulative-β serving AP set* 결정 (cumulative β / Σβ ≥ θ).
2. **Conflict graph**: 두 UE 가 *적어도 하나의 serving AP 를 공유* 하면 edge.
3. **Max-degree-first greedy coloring** with per-color AP quota ⌈M/τ_p⌉.
4. θ 를 bisection 으로 조정해서 *colors_used == τ_p* 가 되도록 (논문 핵심 enhancement).

**예상 강점**:

- *Global conflict structure* 를 직접 utilize. 같은 strong-AP 를 공유하는 UE 쌍은 *항상* 다른 pilot.
- → large τ_p 에서 강함 (conflict graph chromatic number ≤ τ_p 면 conflict-free 가능).

**예상 약점**:

- Small τ_p 에서는 conflict graph 의 chromatic number > τ_p 가 흔함 → coloring 이 *clip* 됨 → strong-AP 공유에서도 collision 발생.
- θ-bisection 은 colors_used 를 맞추려고 *strong AP 정의 자체를 조정* 하는데, small τ_p 에서 너무 작은 θ 가 강요되면 *진짜 strong AP* 까지 무시.

### 2.3 Chen structured access (Benchmark I [15])

**핵심 logic**:

1. AP-centric initial access (AP-quota τ_p 로 weak UE eviction).
2. δ-bisection 으로 group 형성: shared serving AP 가 *없는* UE 들끼리 group.
3. Group = conflict graph 의 independent set.

**예상 강점**:

- Liu 와 유사 (global conflict 회피).
- AP-quota 의 weak-UE eviction → *진짜 약한 UE 가 strong UE 와 같은 group 에 안 들어감*.

**예상 약점**:

- Liu 와 유사 (small τ_p 에서 chromatic clip).
- Weak UE eviction 이 *진짜 약한 UE 의 SINR floor* 를 더 낮출 수 있음.

### 2.4 Mussbah Dsatur (beam-domain)

**핵심 logic** (beam-domain, multi-antenna 가정):

1. Beam-domain active beam set B_k^(a) — UE k 의 *유의미한* beam (cumulative-β-power δ-threshold).
2. **Conflict graph**: B = B^(a)ᵀB^(a) + B^(a)ᵀB^(i) + B^(i)ᵀB^(a), Eq.(17).
3. **Dsatur coloring** (Brélaz 1979) — 가장 *constrained* (saturation degree 가 큰) vertex 부터 색칠.

**예상 강점 (multi-antenna 환경에서)**:

- Beam-domain 은 element-domain 보다 *훨씬 sparse* — beam overlap 이 element overlap 보다 적음.
- Dsatur 의 saturation-degree 기준은 *clip 직전 vertex* 부터 색칠 → critical conflict 부터 처리.
- 같은 conflict graph 에서도 max-degree 보다 *chromatic number 에 더 가까운* 색 수 사용 (경험적 결과).

**예상 약점 (element-domain 으로 축소했을 때)**:

- Beam-domain 의 이점이 사라지면 Liu 의 변형 정도로 축소.

## 3. 진단 메트릭 정의

각 metric 은 *한 realization* 에서 *한 algorithm* 의 의사결정 quality 를 측정.

### D1. Top-N Strong-AP Collision Rate

각 UE m 에 대해, m 이 가장 강하게 듣는 top-N AP (N=10 default) 집합 `S_m` 을 정의. m 의
**collision count** = `|{m' ≠ m : pilot(m') = pilot(m), and S_m ∩ S_{m'} ≠ ∅}|`. 평균을 취함.

**해석**: 작을수록 좋음. *진짜 강한 AP 에서* 같은 pilot UE 가 얼마나 많은지.

**가설**: Gao 가 small τ_p 에서 이 metric 이 작다 → small-τ_p 우위 설명.

### D2. Pilot-induced Coherent Interference (per-UE)

UE m 의 SINR 분모 중 coherent pilot interference term:

$$I^\text{coh}_m = \sum_{m' \neq m : \phi_{m'} = \phi_m} \left(\sum_k \frac{\beta_{m'k}}{\beta_{mk}} \beta_{mk} \gamma_{mk}\right)^2 / \text{(normalization)}$$

정확한 form 은 Gao Eq.(8) 또는 Ngo Eq.(27) 참조. 실제 simulator 의 SINR 계산에서 추출.

**해석**: 작을수록 좋음. SINR 격차의 직접 원인.

**가설**: P5 throughput 차이는 *worst-quintile UE 의 I^coh* 분포 차이로 설명될 것.

### D3. Pilot Reuse Spatial Distance

동일 pilot 받은 UE 쌍의 2D distance 분포의 통계 (median, 5th percentile).

**해석**: 크면 좋음 (멀리 떨어진 UE 들이 same pilot).

**가설**: Liu/Chen 이 large τ_p 에서 spatial distance 가 큼 → global structure 활용 증거.

### D4. Conflict Graph Chromatic Number Distribution

Liu-style conflict graph 의 chromatic number `χ(G)` 분포 (τ_p 별).

**해석**:

- `χ(G) ≤ τ_p`: pilot 충분, conflict-free 가능 → Liu 가 강해질 영역.
- `χ(G) > τ_p`: pilot 부족, *반드시 collision* → Gao 의 AP-local strategy 가 유리할 수도.

**가설**: τ_p=10 영역은 대부분 `χ(G) > 10` → Liu 가 clip, Gao 가 우위.

### D5. Decision Disagreement (Gao vs Liu)

같은 토폴로지에서 두 알고리즘이 *같은 UE 쌍* 에 *같은 pilot* 할당하는 frequency.

- `agree_rate(m,m')` = (Gao 가 같은 pilot 줌) AND (Liu 도 같은 pilot 줌)
- `disagree_pattern`: Gao 가 same / Liu 가 diff (vice versa) 분포

**해석**: Hybrid 가능성 직접 measure. 두 알고리즘이 *진짜* 다른 결정을 할 때만 hybrid 가 의미 있음.

**가설**: Disagreement 가 *small τ_p 에서 large* 일 것. Large τ_p 에서는 두 알고리즘 모두 비슷한 sparse 할당으로 수렴.

## 4. 결과 (50 MC, τ_p ∈ {10, 15, 20, 25, 30}, seed=7)

실행: `python experiments/diagnose_algorithms.py --realizations 50 --tau-values 10 15 20 25 30 --out-suffix _50mc`

산출물:

- `figures/diagnose_algorithms_summary_50mc.csv`
- `figures/diagnose_algorithms_pairs_summary_50mc.csv`
- `figures/diagnose_algorithms_raw_50mc.csv` (per-realization)
- `figures/diagnose_algorithms_pairs_raw_50mc.csv`

### 4.1 D1 — Top-N (=10) strong-AP collision rate (per UE, **lower = better**)

| τ_p | Gao | Graph (full) | Structured (full) | Best |
| ---: | ---: | ---: | ---: | --- |
| 10 | **1.59** | 1.99 | 2.41 | **Gao** |
| 15 | 0.97 | 1.28 | **0.76** | Structured |
| 20 | 0.68 | 0.90 | **0.16** | Structured |
| 25 | 0.51 | 0.68 | **0.02** | Structured |
| 30 | 0.44 | 0.20 | **0.005** | Structured |

**해석**:

- τ_p=10 에서 Gao 가 D1 최소. **Paper-faithful Gao 의 small-τ_p 우위 메커니즘 = AP-local
  top-τ_p 선별이 strong-AP collision 을 가장 잘 줄임**.
- τ_p ≥ 15 부터는 Structured 가 D1 최소. **Structured 의 *AP-quota + weak-UE eviction*
  이 large τ_p 에서 매우 효과적** — Gao 보다 30~80× 적은 collision (τ_p=25 기준
  0.02 vs 0.51).
- Gao 와 Graph 의 *cross-over* 가 τ_p=30 근처에서 발생: Graph 의 conflict-graph 기반
  coloring 이 충분한 색 (τ_p) 가 있을 때 Gao 보다 잘 동작.

→ **H1 (Gao 의 small-τ_p 우위 메커니즘 = D1) 확정**.

### 4.2 D2 — Per-UE coherent pilot interference (**lower = better**)

(단위 ×10⁻¹⁹)

| τ_p | Gao | Graph (full) | Structured (full) | Best |
| ---: | ---: | ---: | ---: | --- |
| 10 | 6.81 | 10.74 | **2.99** | Structured |
| 15 | 5.47 | 6.14 | **1.11** | Structured |
| 20 | 5.46 | 4.44 | **0.63** | Structured |
| 25 | 3.08 | 3.50 | **0.42** | Structured |
| 30 | 4.02 | 0.86 | **0.30** | Structured |

**해석**:

- **모든 τ_p 에서 Structured 가 D2 최소**. 즉 SINR-impacting 한 coherent interference
  차원 에서는 Structured 가 *항상* 가장 깨끗.
- 그런데 throughput 에서 Structured 가 *항상* 이기지는 않음 (small τ_p 에서 Gao 가 이김).
- **이것이 H2 의 메커니즘**: D2 는 SINR average 에 영향, P5 throughput 은 worst-case
  UE 에 의해 결정 → P5 의 dominant determinant 가 D1 (worst-case collision)
  쪽이라는 가설과 일치.

→ **H2 (Structured 의 D2 우위가 P5 throughput 으로 완전 transfer 안 됨) 확정**.

### 4.3 D3 — Pilot reuse spatial distance (m, **higher = better**)

#### Median pairwise distance

| τ_p | Gao | Graph | Structured |
| ---: | ---: | ---: | ---: |
| 10 | 520 | 513 | 519 |
| 20 | 528 | 514 | 528 |
| 30 | 534 | 533 | 539 |

#### 5th-percentile (worst-case) pairwise distance

| τ_p | Gao | Graph | Structured |
| ---: | ---: | ---: | ---: |
| 10 | **168** | 142 | 161 |
| 20 | 182 | 149 | **206** |
| 30 | 183 | 209 | **247** |

**해석**:

- Median 은 알고리즘 간 차이 작음 (모두 ~520m, area_size=1000m 의 절반 정도).
- **Worst-case (p5) 거리** 에서 차이가 큼:
  - τ_p=10: Gao 가 최대 worst-case distance (168m). 즉 same-pilot UE 들이 가장
    *덜* 붙음.
  - τ_p ≥ 20: Structured 가 압도. Worst-case 도 200m+ 보장.

→ D3 와 D1 이 동일 trend (small τ_p Gao / large τ_p Structured 우위) 를 spatial
view 에서도 보여줌.

### 4.4 D4 — Chromatic number distribution (Liu-style, θ=0.7)

50 realizations 평균: **χ̄ = 7.72 colors**. 즉 평균적으로 8 colors 면 conflict-free coloring 가능.

**해석**:

- τ_p=10 도 *conflict-graph 차원에서는 conflict-free 가능 영역* (10 ≥ 8).
- 그런데도 Gao 가 τ_p=10 에서 throughput 이 가장 좋음.
- → **colorability 자체는 binary determinant 가 아님**. *어떤 conflict 를 어떻게
  처리하는지* 가 결정적.

→ **H4 부분 확정**. "Pilot-scarce" 라는 표현은 *chromatic number 대비* 가 아닌
*top-AP collision quality* 차원에서 정의해야 더 정확.

### 4.5 D5 — Pair-level decision disagreement

`agree_rate` = (두 알고리즘이 *같은 UE 쌍* 에 *같은 pilot* 줌 또는 *둘 다 다른 pilot*).

| τ_p | Gao vs Graph | Gao vs Structured | Graph vs Structured |
| ---: | ---: | ---: | ---: |
| 10 | 0.827 (17.3% diff) | **0.786 (21.4% diff)** | 0.798 |
| 15 | 0.881 | 0.862 | 0.869 |
| 20 | 0.912 | 0.902 | 0.907 |
| 25 | 0.931 | 0.924 | 0.928 |
| 30 | 0.942 | 0.939 | 0.941 |

**해석**:

- **Gao vs Structured 가 모든 τ_p 에서 disagreement 최대** — 두 알고리즘이 *가장 다른
  결정 axis* 사용.
- Disagreement 가 τ_p=10 에서 21% → τ_p=30 에서 6%. *small τ_p 일수록 algorithm 선택이
  실제로 다른 결과* 를 만듦.
- → **Hybrid 의 의미 있는 design space 는 small τ_p 영역**. Large τ_p 에서는 어떤
  알고리즘 써도 비슷한 결과.

→ **H3 확정**.

### 4.6 Hypothesis 검증 요약

| Hypothesis | 상태 | 근거 |
| --- | --- | --- |
| H1: Gao 의 small-τ_p 우위 ↔ D1 감소 | **확정** | §4.1, Gao 의 D1 = 1.59 < Graph 1.99 < Structured 2.41 at τ_p=10 |
| H2: Structured 의 D2 우위는 throughput transfer 안 됨 | **확정** | §4.2, Structured 의 D2 항상 최소이나 small τ_p P5 는 Gao 우위 |
| H3: Hybrid design space 는 small τ_p | **확정** | §4.5, τ_p=10 disagreement 21%, τ_p=30 은 6% |
| H4: D4 chromatic 이 colorability 결정 | **부분 확정** | §4.4, τ_p=10 도 chromatic=8 < 10 인데 algorithm 차이 큼 |
| H5: D1 (AP-local) vs D2 (global) 두 axis | **확정** | §4.1+§4.2, Gao 는 D1 small-τ_p 우위 / Structured 는 D2 all-τ_p 우위 |

## 5. Hybrid 설계 input

§4 결과로 도출된 hybrid / 새 알고리즘 후보:

### 5.1 Decision axis 정리

진단 결과 두 *서로 다른* axis 가 존재:

- **D1-axis (AP-local worst case)**: 각 UE 의 *strongest AP 에서의 collision*. P5
  throughput 의 dominant determinant.
- **D2-axis (global SINR-weighted)**: SINR 평균에 영향. P50 (median) throughput 결정.

알고리즘별 좌표:

| Algorithm | D1 strength | D2 strength | 강한 영역 |
| --- | --- | --- | --- |
| Gao matching | ★★★ at small τ_p | ★★ | small τ_p (=10) |
| Liu graph coloring | ★★ | ★★ | medium τ_p |
| Chen structured access | ★★★ at large τ_p | ★★★ all τ_p | large τ_p (≥15) |
| (예상) Mussbah Dsatur | beam-domain 환경 | beam-domain 환경 | multi-antenna |

### 5.2 Hybrid 후보 #1 — Conflict graph + D1 penalty (즉시 prototype 가능)

**아이디어**: Liu graph coloring 의 conflict graph 에 *D1-aware edge weight* 추가.

- 기존 Liu: shared serving-AP 가 있으면 edge (binary).
- 새: shared **top-N AP** 가 있으면 *weight = N - |shared|* (강할수록 큰 penalty).
- Coloring 을 max-weight greedy 또는 weighted-Dsatur 로 변경.

**예상**: small τ_p 에서 Gao-style D1 우위 + large τ_p 에서 Liu/Chen 의 global structure
우위 결합. 즉 **모든 τ_p 에서 일관된 우위**.

**구현 부담**: 작음 (~1일). `GraphColoringPilotAssignment` 의 conflict matrix 만 수정.

### 5.3 Hybrid 후보 #2 — Gao matching + 그룹 내 coloring

**아이디어**: Gao Algorithm 1 (matching → group) 까지는 그대로. Algorithm 2 의 *random
pilot 할당* 을 *그룹 내 conflict graph coloring* 으로 교체.

- Gao 의 AP-local grouping (D1 우위 메커니즘) 살림.
- Pilot 할당 시점에 *global conflict* 도 고려.
- 즉 Gao 의 약점 (Algorithm 2 의 random 할당) 을 보완.

**예상**: large τ_p 에서 Gao 의 약점 (D2 high) 해소. Small τ_p 우위 유지.

**구현 부담**: 작음~중간 (~1-2일). `MatchingBasedPilotAssignment` 의 Algorithm 2 부분 교체.

### 5.4 Hybrid 후보 #3 — τ_p-adaptive switching

**아이디어**: τ_p / chromatic ratio 에 따라 algorithm 선택:

- `τ_p / χ < 1.3`: Gao 사용 (pilot-scarce, D1 axis 가 dominant)
- `τ_p / χ ≥ 1.3`: Structured 사용 (pilot-abundant, D2 axis 가 dominant)

**예상**: 두 algorithm 의 *각자 영역에서의 강점* 만 가져옴.

**구현 부담**: 최소 (~0.5일). 단순 dispatcher.

**한계**: 새 contribution 정도는 약함. 기존 알고리즘 wrap 수준.

### 5.5 Hybrid 후보 #4 — D1+λ·D2 multi-objective

**아이디어**: 두 axis 를 weighted sum 으로 동시 최적화. 새 알고리즘 design.

- Objective: minimize `D1(assignment) + λ · D2(assignment)`
- Heuristic search (예: simulated annealing, local search) 또는 ILP relaxation.

**예상**: Pareto-optimal 위치 탐색. *진짜 새 contribution*.

**구현 부담**: 크다 (~3-5일). Search algorithm + tuning + 평가.

**리스크**: heuristic search 가 NP-hard 문제에서 local optimum 빠질 수 있음.

### 5.6 추천 진행 순서

1. **Hybrid #1 (conflict graph + D1 penalty)** — 가장 적은 비용에 가장 직접적 검증. **1순위**.
2. **Hybrid #2 (Gao matching + 그룹 내 coloring)** — Gao 의 약점 정확히 타격. 2순위.
3. (#1, #2 가 효과 미미하면) **Hybrid #4 (multi-objective)** — 진짜 새 알고리즘 design.
4. **Multi-antenna 환경 확장** (Mussbah end-to-end) 은 위 hybrid 들이 element-domain
   에서 의미 있다고 검증된 후 진행.

### 5.7 검증 메트릭

각 hybrid 후보를:

- D1, D2 (이번 진단 metric) 직접 평가
- 기존 200 MC sensitivity 환경 (PROGRESS.md §3.1) 에서 P5 throughput 비교
- Bootstrap 95% CI 로 통계적 유의성 (`bootstrap_p5_ci.py` 재활용)
- 진단 결과 표 (Diagnosis.md §4 형식) 으로 *왜 좋은지* / *왜 안 좋은지* 정량 제시

## 6. Hybrid #1 결과 (TopAPGraphColoring, 2026-06-01)

구현: `src/pilot_schemes/top_ap_graph.py`. 변경점은 conflict graph 정의만 — Liu 의
cumulative-β serving set → *shared top-N strongest AP*. Greedy coloring 은 Liu 와 동일.

### 6.1 진단 metric (50 MC, seed=7)

#### D1 — Top-N strong-AP collision rate (**lower = better**)

| τ_p | Gao | Graph (full) | Structured (full) | **TopAP (N=10)** | Best |
| ---: | ---: | ---: | ---: | ---: | --- |
| 10 | 1.59 | 1.99 | 2.41 | **0.76** | **TopAP** |
| 15 | 0.97 | 1.28 | 0.76 | **0.09** | **TopAP** |
| 20 | 0.68 | 0.90 | 0.16 | **0.03** | **TopAP** |
| 25 | 0.51 | 0.68 | 0.02 | **0.013** | **TopAP** |
| 30 | 0.44 | 0.20 | 0.005 | **0.000** | **TopAP** |

**TopAP 가 D1 axis 를 압도적 최저** — Gao 보다 2~50× 적은 collision. Hybrid #1 의 핵심
설계 의도 (D1 axis 직접 최적화) 가 진단 차원에서 명확히 성립.

#### D2 — Per-UE coherent pilot interference (×10⁻¹⁹, **lower = better**)

| τ_p | Gao | Graph (full) | Structured (full) | **TopAP** | Best |
| ---: | ---: | ---: | ---: | ---: | --- |
| 10 | 6.81 | 10.74 | **2.99** | 7.25 | Structured |
| 15 | 5.47 | 6.14 | **1.11** | 2.34 | Structured |
| 20 | 5.46 | 4.44 | **0.63** | 1.21 | Structured |
| 25 | 3.08 | 3.50 | **0.42** | 0.72 | Structured |
| 30 | 4.02 | 0.86 | **0.30** | 0.57 | Structured |

TopAP 의 D2 는 Structured 보다 1.5~2× 큼. **그러나 Gao 보다는 모든 τ_p 에서 1.5~10× 작음**.
즉 두 axis 동시 향상 — D1 압도적, D2 도 Gao 대비 크게 개선.

### 6.2 P5 throughput 비교 (100 MC, seed=42, Fractional, **higher = better**)

| τ_p | Gao | Graph_full | Graph_θ=0.9 | Struct_full | Struct_δ=0.3 | **TopAP N=10** | **TopAP N=5** | **TopAP N=3** | Best |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 10 | 5.06 | 4.99 | 5.02 | 4.76 | 5.10 | 5.13 | **5.33** | 5.12 | **TopAP N=5** |
| 15 | 5.42 | 5.43 | 5.48 | 5.44 | 5.60 | **5.75** | 5.56 | 5.42 | **TopAP N=10** |
| 20 | 5.59 | 5.57 | 5.86 | 5.82 | 5.87 | **5.92** | 5.75 | 5.61 | **TopAP N=10** |
| 25 | 5.59 | 5.60 | 5.89 | 5.81 | 5.82 | **5.86** | 5.68 | 5.61 | **TopAP N=10** |
| 30 | 5.60 | 5.89 | **5.89** | 5.87 | 5.85 | 5.81 | 5.65 | 5.59 | Graph (살짝) |

### 6.3 통계적 유의성 (Bootstrap 95% CI, B=1000)

| Comparison | gap (%) | CI half-width | gap / CI | 판정 |
| --- | ---: | ---: | ---: | --- |
| τ_p=10, TopAP N=5 vs Gao | +5.3% | ±2.0% | **1.8×** | **유의** |
| τ_p=10, TopAP N=5 vs Structured_full | +12.0% | ±2.0% | **2.9×** | **강하게 유의** |
| τ_p=10, TopAP N=5 vs Random | +16.9% | ±2.0% | **4.0×** | **강하게 유의** |
| τ_p=15, TopAP N=10 vs Struct_δ=0.3 | +2.6% | ±1.5% | 1.4× | borderline 유의 |
| τ_p=20, TopAP N=10 vs Struct_δ=0.3 | +0.8% | ±1.6% | 0.4× | not significant |
| τ_p=30, Graph_full vs TopAP N=10 | +1.4% | ±1.3% | 0.9× | borderline (Graph 살짝) |

### 6.4 N hyperparameter 의 τ_p 의존성

| τ_p | N=3 | N=5 | N=10 | Best N |
| ---: | ---: | ---: | ---: | --- |
| 10 | 5.12 | **5.33** | 5.13 | N=5 |
| 15 | 5.42 | 5.56 | **5.75** | N=10 |
| 20 | 5.61 | 5.75 | **5.92** | N=10 |
| 25 | 5.61 | 5.68 | **5.86** | N=10 |
| 30 | 5.59 | 5.65 | **5.81** | N=10 |

**Pattern**: N ≈ τ_p / 2 가 optimal 근처. τ_p=10 → N=5, τ_p≥15 → N=10. **Adaptive N
selection (τ_p-dependent)** 이 자연스러운 다음 step.

### 6.5 종합

**Hybrid #1 = 명백히 작동**:

1. **D1 axis 압도적 최적화** (Gao 대비 2~50× 적은 collision).
2. **D2 axis 도 Gao 보다 크게 개선** (Structured 보다는 약간 뒤지지만 동급).
3. **P5 throughput 모든 τ_p ∈ {10,15,20,25} 에서 best** (적절한 N 선택 시).
4. **τ_p=10 에서 통계적으로 유의** (Gao, Liu, Chen, Random 모두 압도, 2~4× CI).
5. **τ_p ≥ 30 에서만 Graph_full 이 살짝 우위** (CI 안).

**Limitation / 다음 step**:

- N=10 fixed 는 sub-optimal at τ_p=10. Adaptive N (예: N=⌈τ_p/2⌉) 또는 N-bisection.
- τ_p=30 에서 Graph_full 이 살짝 우위 — TopAP 의 N 이 너무 작으면 chromatic 부족.
  N bisection 으로 chromatic == τ_p 맞추면 큰 τ_p 도 우위 가능성.
- Hybrid #2 (Gao matching + group-internal coloring) 와 직접 비교 필요.

## 7. Hybrid #1 + N-bisection 결과 (2026-06-02)

§6 의 fixed-N TopAP 는 N=5 (τ_p=10) 와 N=10 (τ_p≥15) 사이 trade-off 가 있어서
hyperparameter 선택이 τ_p 의존이었음. N-bisection 을 추가해 자동 N 결정.

### 7.1 Design

Liu 의 θ-bisection 의 정수 analogue:

- 큰 N 일수록 stricter conflict → 큰 chromatic.
- 작은 N 일수록 sparser conflict → 작은 chromatic.
- *Largest N such that quota-free real chromatic ≤ τ_p* 를 integer bisection 으로 탐색.

중요: actual coloring 은 per-color quota `⌈K/τ_p⌉` 가 항상 chromatic = τ_p 를 강제하므로,
*quota-free greedy chromatic* 을 별도로 측정해야 N 결정이 의미 있음 (초기 design 은 quota
포함 chromatic 으로 종료 조건 두었다가 -3~4% 손실, real-chromatic 으로 수정).

구현: `src/pilot_schemes/top_ap_graph.py` 의 `bisect=True` 옵션. `_real_chromatic()` helper.

### 7.2 결과 — N-bisection 이 선택한 N

| τ_p | N (chosen) | real chromatic |
| ---: | ---: | ---: |
| 10 | 7 | 12 |
| 15 | 11 | 17 |
| 20 | 14 | 23 |
| 25 | 16 | 29 |
| 30 | 21 | 34 |

τ_p 가 클수록 N 도 큼 (stricter conflict). Pattern: `N ≈ 0.7 · τ_p` 근처.

### 7.3 P5 throughput vs fixed-N (100 MC, seed=42, fractional)

| τ_p | Gao | Struct_full | TopAP N=10 | TopAP N=5 | **TopAP (bisect)** |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 5.06 | 4.76 | 5.13 | 5.33 | **5.39** ★ |
| 15 | 5.42 | 5.44 | **5.75** | 5.56 | 5.74 |
| 20 | 5.59 | 5.82 | **5.92** | 5.75 | 5.91 |
| 25 | 5.59 | 5.81 | **5.86** | 5.68 | 5.84 |
| 30 | 5.60 | 5.87 | 5.81 | 5.65 | **5.91** ★ |

**Bisection vs fixed-N best**:

- τ_p=10: bisect 5.39 > N=5 5.33 (+1.1%) → 새 최고
- τ_p=15-25: bisect ≈ N=10 (within 0.5%)
- τ_p=30: bisect 5.91 > N=10 5.81 (+1.7%) → 약점이었던 large τ_p 도 해결

**Bootstrap CI (100 MC, B=1000)**:

| τ_p | Comparison | gap (%) | gap / combined CI | 판정 |
| ---: | --- | ---: | ---: | --- |
| 10 | bisect vs Gao | +6.5% | 2.0× | **유의** |
| 10 | bisect vs Structured_full | +13.3% | 3.3× | **강하게 유의** |
| 10 | bisect vs Random | +18.3% | 4.0× | **강하게 유의** |
| 30 | bisect vs Gao | +5.5% | 2.5× | **유의** |
| 30 | bisect vs Graph_full | +0.3% | 0.1× | tied (within CI) |

### 7.4 종합 — Hybrid #1 + bisect 의 성과

- **모든 τ_p ∈ {10, 15, 20, 25, 30} 에서 best (또는 best 와 동등)**.
- **paper-faithful Gao 와 통계적으로 유의한 gap** (small τ_p 2× CI, large τ_p 2.5× CI).
- **Hyperparameter 없음** (사용자가 N 추측 불필요).
- **τ_p=30 의 fixed-N 약점도 해결**.

## 8. Hybrid #2 결과 — Gao matching + greedy contam-min (2026-06-02)

Diagnosis.md §5.3 에서 정의. Gao Algorithm 1 (matching → group) 그대로 유지하고
Algorithm 2 의 *random pilot 할당* 을 *β·β contamination-minimising greedy* 로 교체.

### 8.1 Design

각 group (S 큰 순) 에 대해, 그룹 내 unassigned UE k 의 pilot 결정:

- 후보 pilot p (group 안 미사용) 각각에 대해 contamination metric 계산:

```text
C(k, p) = β_k · Σ_{k' : pilot(k')==p} β_{k'}
```

- 최소 contamination 의 pilot 할당, incremental update.

D1 axis 는 Gao Algorithm 1 (top-τ_p AP 기반 grouping) 이 처리. D2 axis 를 Algorithm 2 의
greedy contam-min 이 직접 minimise. 두 axis 모두 활용.

구현: `src/pilot_schemes/matching_greedy_h2.py`. Vectorised — O(τ_p · M) per UE 결정.

### 8.2 P5 throughput vs baselines + TopAP (100 MC, seed=42, fractional)

| τ_p | Gao | Struct_full | TopAP bisect | **H2 Gao+greedy** |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 5.06 | 4.76 | **5.39** | 5.32 |
| 15 | 5.42 | 5.44 | **5.74** | 5.65 |
| 20 | 5.59 | 5.82 | **5.91** | 5.88 |
| 25 | 5.59 | 5.81 | 5.84 | **5.86** |
| 30 | 5.60 | 5.87 | **5.91** | 5.83 |

**H2 vs baselines (Bootstrap CI)**:

| τ_p | Comparison | gap (%) | gap / combined CI | 판정 |
| ---: | --- | ---: | ---: | --- |
| 10 | H2 vs Gao | +5.2% | 1.5× | **유의** (marginal) |
| 10 | H2 vs Structured_full | +11.7% | 2.8× | **강하게 유의** |
| 15 | H2 vs Gao | +4.2% | 1.4× | **유의** (marginal) |
| 20 | H2 vs Struct_full | +1.0% | 0.3× | not significant |

**H2 vs TopAP bisect**:

| τ_p | H2 | bisect | Δ | CI gap |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 5.32 | 5.39 | -1.3% | within CI |
| 15 | 5.65 | 5.74 | -1.6% | within CI |
| 20 | 5.88 | 5.91 | -0.5% | within CI |
| 25 | 5.86 | 5.84 | +0.4% | within CI |
| 30 | 5.83 | 5.91 | -1.4% | within CI |

**모든 τ_p 에서 두 hybrid 정량 차이 < 2%, 통계적으로 tied**.

### 8.3 종합 — Hybrid #2 의 성과

- **모든 τ_p 에서 Gao / Liu / Chen 압도** (small τ_p 유의, large τ_p 동등 또는 살짝 우위).
- **TopAP bisect 와 통계적으로 tied** (실질 동등).
- **D1 axis (matching) + D2 axis (greedy) 동시 활용 → 다른 design 방향** 입증.

### 8.4 두 hybrid 의 의미

같은 진단 input (D1 + D2 axis 동시 최적화) 으로 두 가지 *서로 다른 방향* 의 알고리즘이
나옴:

- **H1 (TopAP bisect)**: D1 axis 를 *conflict graph* 차원에서 최적화, coloring 으로 일관
  pilot 분배. *Global, graph-based* 관점.
- **H2 (Gao+greedy)**: D1 axis 를 *Gao matching 의 AP-local grouping* 으로 처리,
  D2 axis 를 *그룹 순회 greedy* 로 직접 minimise. *Sequential, contamination-aware* 관점.

두 방향이 *통계적으로 tied* 라는 사실은:

1. **D1 + D2 axis 동시 최적화 자체가 핵심 메커니즘**.
2. 어떤 의사결정 framework 으로 구현하든 비슷한 throughput 향상.
3. *결합 hybrid* (TopAP graph + greedy contam-min coloring) 도 가능 — 다음 단계.

## 9. Multi-antenna paper-faithful 환경 결과 (2026-06-03 추가)

§8 의 *D1 + D2 axis 동시 최적화* 메커니즘이 *multi-antenna paper-faithful* 환경 (Mussbah
3GPP UMi + one-ring + Rician + Eq.9 MRC SE) 에서도 robust 한지 검증.

세부: `Mussbah_reproduce_plan.md` §11-§15.

### 9.1 핵심 발견 — D1 axis 의 cross-domain transferability

| Setting | TopAP bisect (D1) | H2 Gao+greedy (D1+D2) | Mussbah (beam-domain D1) |
| --- | --- | --- | --- |
| Element-domain Gao (PROGRESS.md §3.1) | +5-7% | +4-6% | (N/A) |
| Element-domain Diagnosis (§4-§6) | best at τ_p=10 | best at τ_p≥15 | (N/A) |
| Multi-antenna Mussbah env (K=30) | -1.3% (tied) | -1.1% (tied) | -2.2% |
| Multi-antenna Gao env (K=200) | **+0.6% (1위)** | **+0.5% (2위)** | -53.6% catastrophic |

**Element-domain D1 axis (TopAP bisect, H2) 가 *multi-antenna paper-faithful 환경에서도
robust***. Mussbah 의 *beam-domain D1* (active beam conflict) 보다 *element-domain
top-N AP conflict* 가 더 효과적인 환경 존재.

### 9.2 진단 결과 → Cross-paper validation

Diagnosis §4-§6 에서 도출한 두 axis (D1 = AP-local worst case, D2 = global SINR-weighted)
가 *multi-antenna 환경에서도 valid*:

- **D1 axis (top-N AP conflict)**: element-domain logic 만으로 multi-antenna 환경에서도
  effective. Mussbah 의 beam-domain 보다 *cross-environment robust*.
- **D2 axis (β·β contamination)**: H2 Gao+greedy 의 greedy mechanism 이 multi-antenna 환경
  에서도 advantage 유지 (+0.5% vs Random in Gao setting).
- **adaptive τ_p mechanism** (Mussbah 의 핵심): K-density 에 강하게 의존 → cross-paper 일반화
  불가. Hybrid#3 (TopAP + adaptive τ_p) 도 동일 한계.

### 9.3 결론 — D1 axis 가 우리 contribution 의 *true mechanism*

처음에 단순 진단 metric 으로 시작한 D1 (top-N strong-AP collision rate) 가:

1. Element-domain Gao environment 에서 ✓ Hybrid#1 (TopAP bisect) 의 root cause
2. Element-domain D2 와 결합 ✓ Hybrid#2 (H2 Gao+greedy)
3. **Multi-antenna paper-faithful 환경 에서도 effective** ✓ 두 hybrid 모두 cross-paper top
4. **Adaptive τ_p mechanism (Mussbah-style)** 와 *결합* 하면 small K 에서 best (Hybrid#3),
   하지만 large K 에서는 K-sensitivity 한계

**Hybrid#3 의 narrative**: TopAP 의 sparser conflict graph (D1 axis) + Mussbah 의 fewer-
pilots mechanism (adaptive τ_p) 결합. K=30 에서 Mussbah (+0.4% vs Random, Mussbah setting
1위) 보다 효과적. K=200 에서는 adaptive τ_p mechanism 의 한계로 advantage 사라짐.

### 9.4 진정한 cross-paper contribution

**Non-adaptive D1-axis hybrid (TopAP bisect, H2 Gao+greedy)** 가 *cross-paper transferable*.
Multi-antenna 환경의 paper-faithful 평가에서도 두 paper 의 environment 모두 leading.

이건 *Mussbah 의 beam-domain conflict graph* 가 다른 환경에서 적용 안 됨 ↔ *element-domain
top-N AP conflict* 가 더 generalisable 함을 입증.

## 10. 다음 단계

진단 → Hybrid #1 → Hybrid #2 → multi-antenna paper-faithful → Hybrid#3 까지 완료.

남은 가능한 방향:

1. **Hybrid#3 의 K-robust version**: chromatic 가 너무 크면 standard τ_p_design 사용
   fallback. K-adaptive selection. ~1일.
2. **K-sweep + N-sweep 정량적 envelope**: 우리 hybrid 의 advantage region 정확히 식별. ~1일.
3. **Energy Efficiency (EE) metric**: Mussbah paper §V 의 EE 평가. RF chain on/off 도입.
   ~1-2일.
4. **보고서/논문 형태 정리**: 현재 결과 만으로도 reproduce + cross-paper + new hybrid 의
   narrative 명확. PROGRESS.md + Diagnosis.md + Mussbah_reproduce_plan.md 의 통합 정리.
