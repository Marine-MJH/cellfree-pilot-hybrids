# Project Explained — Cell-Free Massive MIMO Pilot Assignment

이 문서는 **cell-free massive MIMO 를 잘 모르는 사람도** 이 프로젝트가 무엇을 했고,
코드는 어떻게 구성되어 있으며, 결과를 어떻게 읽어야 하는지 한 번에 이해하도록 만든 설명서다.

작성일: 2026-06-04  
대상 프로젝트: 이동통신시스템 과제, `proj_pilot`

주의:

- 이 문서에서 AP 수는 `L`, UE 수는 `K` 로 통일한다. 일부 논문/코드 문서에서는 기호가
  다르게 쓰인다.
- 실험 결과 해석 중 원인 분석은 `[Inference]` 로 표시한다. 이는 실험 수치에서 논리적으로
  해석한 내용이며, 논문 저자가 직접 확인해 준 사실은 아니다.
- 이 프로젝트는 두 논문을 그대로 합쳐서 "완전히 공정한 직접 비교"를 했다고 주장하지 않는다.
  Gao 논문과 Mussbah 논문의 antenna model 이 다르기 때문이다.

## 1. 한 문장 요약

이 프로젝트는 **cell-free massive MIMO 에서 pilot contamination 을 줄이기 위한 pilot assignment
알고리즘**을 다룬다. Gao 2024 와 Mussbah 2024 두 논문을 재현하고, 같은 코드베이스 안에서 여러
알고리즘을 비교한 뒤, 두 논문의 아이디어를 섞은 hybrid 알고리즘을 제안하고 검증했다.

가장 중요한 최종 결론:

- Gao 2024 의 small-pilot advantage 는 비교적 잘 재현됐다.
- Mussbah 2024 의 알고리즘과 multi-antenna channel/SE pipeline 은 구현했지만, 논문 Fig.1 의
  `+8%` 수치를 default 조건에서 그대로 재현하지는 못했다.
- 두 논문은 antenna model 이 달라 직접 비교가 어렵다.
- 그래서 E4 라는 **common-ground unified benchmark**를 새로 만들었다.
- E4 에서 **Hybrid#3 (TopAP N=8 adaptive)** 가 가장 강했다.
- E4 에서 Mussbah 원 알고리즘은 오히려 Random 보다 낮았다.

## 2. 배경: Cell-Free Massive MIMO 란 무엇인가

### 2.1 기존 cellular network 와 다른 점

일반적인 cellular network 는 사용자가 하나의 기지국 또는 몇 개의 기지국에 붙는 구조다. 반면
**cell-free massive MIMO** 는 넓은 지역에 흩어진 많은 AP(access point)가 중앙 처리 장치와
연결되어, 여러 UE(user equipment)를 함께 지원하는 구조다.

쉽게 말하면:

- 기존 cellular: "내가 어느 cell 에 속하는가"가 중요하다.
- cell-free: cell 경계보다 "많은 AP 가 협력해서 UE 를 지원한다"는 관점이 중요하다.

### 2.2 Massive MIMO 에서 channel estimation 이 중요한 이유

AP 가 UE 의 신호를 잘 받으려면 channel 을 알아야 한다. Uplink 에서는 UE 가 짧은 known sequence,
즉 **pilot**을 보내고 AP 가 이를 이용해 channel 을 추정한다.

문제는 coherence block 안에서 서로 직교하는 pilot 의 개수가 제한된다는 점이다. UE 수가 pilot 수보다
많으면 여러 UE 가 같은 pilot 을 재사용한다.

### 2.3 Pilot contamination

서로 다른 UE 가 같은 pilot 을 쓰면 AP 입장에서는 두 UE 의 pilot 이 섞인다. 이 때문에 channel
estimate 가 오염되고, 이후 data transmission 에서 coherent interference 가 생긴다. 이것을
**pilot contamination**이라고 부른다.

Pilot assignment 문제는 다음 질문이다:

> "어떤 UE 들이 같은 pilot 을 써도 상대적으로 덜 손해인가?"

이 프로젝트는 바로 그 assignment 문제를 다룬다.

## 3. 과제 목표

원래 과제 목표는 `task.md` 기준으로 다음과 같다.

1. Gao et al. 논문 reproduce.
2. Mussbah et al. 논문 reproduce.
3. 두 알고리즘을 같은 metric 으로 한 그래프에서 성능 비교.
4. 가능하면 새 아이디어 또는 결합 알고리즘 제안.

이 프로젝트는 위 네 가지를 모두 시도했고, 특히 4번에서 네 가지 hybrid 알고리즘을 만들었다.

## 4. 대상 논문 두 개

## 4.1 Gao et al. 2024

파일:

- `Gao et al. - 2024 - A Matching-Based Pilot Assignment Algorithm for Cell-Free Massive MIMO Networks.pdf`

핵심 설정:

- AP 와 UE 모두 single-antenna.
- 많은 AP 와 많은 UE 가 있는 dense setting.
- pilot assignment 를 many-to-many matching 문제로 본다.
- AP 가 강하게 듣는 UE 들을 우선적으로 구분하려 한다.

이 프로젝트에서 구현한 Gao 알고리즘:

- `src/pilot_schemes/matching_gao.py`
- Gao Fig.2/3/4 재현 실험:
  - `experiments/fig2_cdf.py`
  - `experiments/fig3_vs_pilot_number.py`
  - `experiments/fig4_vs_ue_number.py`
  - `experiments/run_gao_final200.sh`

핵심 재현 결과:

- `tau_p=10`, max-min power 영역에서 Gao 가 Random 대비 **+21.7%**.
- 논문 claim 은 약 **+23%**.
- 따라서 Gao 의 small-pilot advantage 는 꽤 잘 재현됐다.

중요한 한계:

- Gao 가 모든 조건에서 Liu/Chen baseline 보다 항상 좋게 나오지는 않았다.
- 특히 large `tau_p` 영역에서는 Liu/Chen 계열이 비슷하거나 더 강한 경우가 있다.
- 따라서 "Gao 가 항상 최고"라고 말하면 안 된다.

## 4.1.5 Gao 가 참조하는 두 benchmark 알고리즘

Gao 논문은 자신을 *세 알고리즘 (Random, Benchmark I, Benchmark II) 과 비교*하는데, 이 두
benchmark 는 별도 논문에서 가져온 것이다. 우리도 *그 두 paper 의 알고리즘을 paper-faithful
하게 구현* 해서 동일한 비교를 가능하게 했다.

**Liu 2020 (Benchmark II — graph coloring)**:

- 논문: H. Liu, J. Zhang, S. Jin, B. Ai, "Graph coloring based pilot assignment for
  cell-free massive MIMO systems", IEEE TVT 2020.
- 알고리즘: 각 UE 의 *cumulative-β θ-threshold serving AP set* 만들고, *shared AP 가 있으면
  conflict edge*. Max-degree-first greedy coloring 으로 pilot 배정.
- 우리 구현 위치: `src/pilot_schemes/graph_coloring.py`.
- 우리는 *원저자 MATLAB 코드* 직접 따라서 paper-faithful 하게 구현 (`refs/liu2020/`).

**Chen 2023 (Benchmark I — structured access)**:

- 논문: J. Chen et al., "Pilot Contamination Mitigation for AP Clustering-based Pilot
  Assignment", PIMRC 2023.
- 알고리즘: AP 마다 *quota τ_p 의 weak-UE eviction* → δ-bisection group formation 으로
  *conflict graph independent set* 형성.
- 우리 구현 위치: `src/pilot_schemes/structured_access.py`.
- 마찬가지로 원저자 MATLAB 코드 기반 (`refs/chen2021/`).

[Inference] 이 두 baseline 을 *paper-faithful 하게 구현* 한 결과, 우리 Liu/Chen 이 *Gao
논문의 reference 구현보다 강하게* 나왔다. 즉 Gao 논문이 자신의 알고리즘 advantage 를
보여줄 때 *상대적으로 약한 baseline* 과 비교했을 가능성이 있다. 자세한 분석은
`PROGRESS.md §3.1` 참조.

## 4.2 Mussbah et al. 2024

파일:

- `Mussbah et al. - 2024 - Beam-Domain-Based Pilot Assignment for Energy Efficient Cell-Free Massive MIMO.pdf`

핵심 설정:

- AP 는 multi-antenna ULA, 기본 `N=8`.
- Beam-domain 에서 active beam set 을 만든다.
- UE 간 beam overlap 을 conflict graph 로 만들고, Dsatur graph coloring 으로 pilot 을 배정한다.
- 알고리즘은 실제 사용 pilot 수를 adaptive 하게 줄이는 것이 핵심 장점 중 하나다.

이 프로젝트에서 구현한 Mussbah 관련 코드:

- `src/pilot_schemes/beam_domain_mussbah.py`
- `src/network.py` 의 `beam_info`
- `src/pathloss_umi.py`
- `src/mussbah_channel.py`
- `src/mussbah_se.py`

중요한 구현 note:

- one-ring covariance, Rician channel, DFT beam-domain transform, active beam selection,
  beam-domain MMSE/MRC style SE 계산을 구현했다.
- `mussbah_se.py` 는 Monte Carlo 방식으로 SE 를 계산한다.
- 내부 MMSE estimator 에는 diagonal covariance approximation 이 들어간다. 따라서 Mussbah 논문의
  closed-form Eq.(10)-(14)를 완전히 그대로 계산했다고 과장하면 안 된다.

핵심 재현 결과:

- default `tau_p=10`, `K=30`, `L=100`, `N=8` 에서는 논문 claim `+8%`를 그대로 재현하지 못했다.
- 다만 `tau_p_design` 이 충분히 커지는 영역에서는 Mussbah 의 adaptive pilot mechanism 이 살아났다.
- `tau_p=20` 영역에서는 Mussbah 와 Hybrid#3 가 Random 대비 높은 mean SE 를 보였다.

## 5. 왜 두 논문 직접 비교가 어려운가

가장 중요한 fairness 문제는 antenna model 이다.

| 항목 | Gao 2024 | Mussbah 2024 |
| --- | --- | --- |
| AP antenna | single-antenna | multi-antenna ULA, N=8 |
| UE antenna | single-antenna | single-antenna |
| 핵심 정보 | large-scale beta | beam-domain active/inactive set |
| Mussbah algorithm 적용 가능 여부 | 불가능 | 가능 |

Mussbah 알고리즘은 `Network.beam_info()` 를 필요로 한다. single-antenna network 에서는 beam-domain
정보가 없으므로 그대로 평가할 수 없다.

따라서 이 프로젝트는 네 가지 관점으로 결과를 나눴다.

| Environment | 의미 |
| --- | --- |
| E1 | Gao paper original single-antenna reproduce |
| E2 | Mussbah paper original multi-antenna reproduce |
| E3 | Gao-sized network 를 N=8 multi-antenna 로 확장한 stress test |
| E4 | 두 paper original 이 아닌 common-ground unified benchmark |

이 구분이 중요하다. 특히 E4 는 "paper reproduction" 이 아니라 "같은 multi-antenna 환경에서의
algorithm benchmark"다.

## 6. 이 프로젝트에서 구현한 알고리즘

## 6.1 Baseline / paper algorithms

| 이름 | 파일 | 설명 |
| --- | --- | --- |
| Random | `src/pilot_schemes/random_scheme.py` | UE 에 pilot 을 무작위 배정 |
| Upper bound | `src/pilot_schemes/upper_bound.py` | 이상적인 기준선에 가까운 참고용 |
| Gao matching | `src/pilot_schemes/matching_gao.py` | Gao 2024 many-to-many matching 기반 |
| GC (Liu) | `src/pilot_schemes/graph_coloring.py` | Liu 2020 graph coloring benchmark |
| Structured (Chen) | `src/pilot_schemes/structured_access.py` | Chen structured access benchmark |
| Mussbah | `src/pilot_schemes/beam_domain_mussbah.py` | beam-domain conflict graph + Dsatur |

## 6.2 우리 hybrid algorithms

### TopAP (bisect)

파일:

- `src/pilot_schemes/top_ap_graph.py`

아이디어:

- 각 UE 가 가장 강하게 들리는 top-N AP 집합을 만든다.
- 두 UE 의 top-N AP 가 겹치면 conflict edge 를 둔다.
- graph coloring 으로 같은 conflict 를 가진 UE 들이 다른 pilot 을 쓰도록 배정한다.
- `bisect=True` 일 때 N 을 조절해서 pilot budget 에 맞춘다.

[Inference] 이 알고리즘은 "beam-domain" 대신 "element-domain strong AP overlap" 을 본다.
Mussbah 보다 단순하지만, 일부 환경에서는 conflict graph 가 더 sparse 하게 나와 성능이 좋았다.

### H2 Gao+greedy

파일:

- `src/pilot_schemes/matching_greedy_h2.py`

아이디어:

- Gao 의 AP-centric grouping 을 사용한다.
- pilot 선택은 greedy contamination minimization 으로 한다.
- 즉 Gao 의 grouping 과 contamination-aware coloring 을 섞은 방식이다.

### Hybrid#3 (TopAP N=8 adaptive)

파일:

- `src/pilot_schemes/top_ap_graph.py`

아이디어:

- TopAP conflict graph 를 사용한다.
- Mussbah 처럼 actual pilot count 를 adaptive 하게 둔다.
- fixed `tau_p_design` 보다 더 적은 pilot 으로 coloring 되면 training overhead 가 줄어든다.

이 프로젝트에서 가장 중요한 hybrid 다.

핵심 결과:

- E2 Mussbah-like small-K 환경에서 강함.
- E4 common-ground 환경에서 가장 강함.
- 하지만 K 가 커지는 환경에서는 장점이 약해질 수 있다.

### Hybrid#4 (TopAP+greedy)

파일:

- `src/pilot_schemes/hybrid4_topap_greedy.py`

아이디어:

- TopAP conflict graph 를 사용한다.
- adaptive pilot count 를 쓰지 않고, greedy contamination minimization 을 결합한다.

특징:

- Hybrid#3 보다 덜 공격적이다.
- large-K stress test 에서 상대적으로 robust 하게 나왔다.

## 7. 코드 구조

## 7.1 `src/`

| 파일/폴더 | 역할 |
| --- | --- |
| `src/config.py` | simulation parameter dataclass |
| `src/network.py` | AP/UE 위치, path loss, beta, beam powers, beam_info |
| `src/pathloss_umi.py` | 3GPP UMi path loss / LoS-NLoS |
| `src/channel.py` | Gao/Ngo 계열 channel estimation variance |
| `src/metrics.py` | SINR, throughput, CDF, P5 metric |
| `src/power_control.py` | full/fractional/max-min power control |
| `src/simulator.py` | Gao-style simulation wrapper |
| `src/mussbah_channel.py` | one-ring covariance, Rician channel sampling |
| `src/mussbah_se.py` | Mussbah-style MC SE computation |
| `src/pilot_schemes/` | 모든 pilot assignment algorithm |

## 7.2 `experiments/`

| 파일 | 역할 |
| --- | --- |
| `fig2_cdf.py` | Gao Fig.2 style CDF |
| `fig3_vs_pilot_number.py` | Gao Fig.3 pilot number sweep |
| `fig4_vs_ue_number.py` | Gao Fig.4 UE number sweep |
| `benchmark_sensitivity.py` | Liu/Chen implementation sensitivity |
| `diagnose_algorithms.py` | D1/D2/D3/D4/D5 decision-level diagnostics |
| `mussbah_fig1_full.py` | Mussbah Fig.1 style full MC |
| `mussbah_fig3_k_sweep.py` | K sweep / tau_p sweep |
| `cross_paper_full.py` | E2/E3 style cross-paper stress test |
| `cross_paper_unified_E4.py` | E4 common-ground unified benchmark |
| `plot_cross_paper_unified_3env.py` | E2/E3/E4 comparison plot |
| `plot_e4_tau_p_actual.py` | E4 actual pilot count diagnostic |
| `bootstrap_se_ci.py` | SE bootstrap confidence intervals |
| `bootstrap_p5_ci.py` | P5 throughput bootstrap confidence intervals |

## 7.3 `tests/`

현재 테스트 (총 21개):

| 파일 | 무엇을 검증 |
| --- | --- |
| `tests/test_algorithm1.py` | Gao Algorithm 1 (matching) 의 정확성 — *AP k 의 top-τ_p UEs by β* 와 100% 일치 확인 (sanity check) |
| `tests/test_sinr.py` | SINR formula (Gao Eq.8 = Ngo Eq.27) component decomposition + max-min power control |
| `tests/test_pathloss.py` | Ngo 2017 / 3GPP UMi path loss 의 distance dependence |
| `tests/test_mussbah.py` | Mussbah Algorithm 1 (Eq.17/18 + Dsatur) — K_5 complete graph → 5 colors, K_{3,3} bipartite → 2 colors, τ_p adaptation 등 8개 |

검증 명령:

```bash
python -m pytest -q tests/
```

현재 확인 결과:

```text
21 passed
```

[Inference] 모든 핵심 algorithm 의 *correctness sanity check* 가 unit test 로 묶여 있어, 코드
수정 시 즉시 regression 잡힘. 새 algorithm 추가 시 비슷한 sanity check 1개 추가 권장.

## 8. Metric 설명

## 8.1 Throughput / SE

Gao 계열 실험에서는 주로 throughput Mbps 를 본다. Mussbah 계열과 E4 에서는 SE
`bit/s/Hz/user`를 본다.

두 metric 모두 "높을수록 좋다".

## 8.2 P5, 95%-likely metric

P5 는 전체 UE 성능 분포의 5th percentile 이다. 통신 논문에서는 이것을 "95%-likely" 성능이라고
부르는 경우가 많다.

의미:

- 평균 성능이 아니라 나쁜 쪽 사용자 성능을 본다.
- cell-free 에서 fairness 를 볼 때 중요하다.

## 8.3 Mean / Median / P5

| Metric | 의미 |
| --- | --- |
| Mean | 전체 평균. statistical CI 가 비교적 안정적 |
| Median | 중앙 사용자 |
| P5 | 하위 5% 사용자. 변동이 큼 |

이 프로젝트에서는 최종 claim 방어에는 mean SE CI 를 주로 사용한다. P5 는 중요하지만 bootstrap
variance 가 더 크다.

## 8.4 `tau_p_design` vs `tau_p_actual`

`tau_p_design` 은 시스템이 처음 설정한 pilot budget 이다. 예: E4 에서 `tau_p_design=15`.

`tau_p_actual` 은 어떤 알고리즘이 실제로 사용한 pilot 수다. adaptive 알고리즘은 `tau_p_actual` 이
`tau_p_design` 보다 작거나 클 수 있다.

중요한 이유:

SE 에는 training overhead factor 가 있다.

```text
(tau_c - tau_p_actual) / tau_c
```

따라서 pilot 을 너무 많이 쓰면 data transmission 에 쓸 시간이 줄어든다.

## 9. 주요 실험 결과

## 9.1 Gao reproduce 결과

대표 결과:

- 실험 파일: `logs/gao_final200_summary.md`
- 200 Monte Carlo setups
- `tau_p=10`, max-min power
- Gao vs Random: **+21.7%**
- 논문 claim: 약 **+23%**

해석:

- Gao 의 핵심 claim 중 small pilot 영역의 advantage 는 방어 가능하다.
- 그러나 Gao 가 모든 strong baseline 을 항상 이기는 것은 아니다.

## 9.2 Mussbah reproduce 결과

대표 산출물:

- `figures/mussbah_fig1_full_cdf_200setups_umi.png`
- `figures/mussbah_fig1_full_summary_200setups_umi.csv`
- `figures/mussbah_fig1_full_summary_tau20.csv`
- `figures/bootstrap_ci_mussbah_fig1_full_raw_tau20.csv`

default `tau_p=10`, `K=30` 에서는 Mussbah paper 의 `+8%` claim 이 그대로 나오지 않았다.

[Inference] 가장 중요한 원인은 conflict graph chromatic number 와 training overhead 관계다.
논문 환경에서는 Mussbah 가 더 적은 pilot 을 써서 overhead 를 줄였을 가능성이 크지만, 이 프로젝트의
literal/implemented 환경에서는 chromatic 이 더 커져 그 이득이 default 조건에서 약해졌다.

`tau_p=20` 영역에서는 adaptive pilot count 이점이 살아난다.

Mean SE bootstrap CI 예:

| 비교 | 결과 |
| --- | --- |
| Mussbah vs Random, tau_p=20 | +9.7% mean SE, CI 분리 |
| Hybrid#3 vs Random, tau_p=20 | +14.0% mean SE, CI 분리 |

## 9.3 K sweep 결과

대표 산출물:

- `figures/envelope_K_tau10.png`
- `figures/envelope_advantage_vs_random.png`
- `figures/mussbah_fig3_k_sweep_summary_100x10_v3.csv`

핵심:

- K 가 커지면 adaptive pilot count 방식이 손해를 볼 수 있다.
- Mussbah 는 `K=45`에서 Random 보다 평균 SE 가 낮아졌다.
- Hybrid#3 도 K 가 너무 커지면 장점이 줄어든다.
- TopAP / H2 / Hybrid#4 같은 non-adaptive 계열은 large-K 에서 더 안정적으로 나왔다.

## 9.4 E3: Multi-antenna Gao-sized stress test

대표 산출물:

- `figures/cross_paper_full_final.png`
- `figures/cross_paper_full_gao_summary_final.csv`
- `figures/bootstrap_ci_cross_paper_full_gao_raw_final.csv`

설정:

- Gao-sized dense network 를 N=8 multi-antenna 로 확장.
- `K=200`, `L=500`.
- 이건 Gao paper original 이 아니다. Gao original 은 N=1 이다.

핵심 결과:

- Mussbah 는 Random 대비 P5 기준 약 **-53.5%**.
- Hybrid#4 / TopAP / H2 계열이 상위권.

[Inference] dense K=200 환경에서는 Mussbah beam-domain conflict graph 가 지나치게 dense 해지고,
adaptive pilot count 이점이 사라지거나 손해가 된다.

## 9.5 E4: Common-ground unified benchmark

대표 산출물:

- `figures/cross_paper_unified_E4_summary_E4.csv`
- `cross_paper_unified_E4_raw_E4.csv` — cleanup 이후에는
  `.artifact_archive/cleanup_2026-06-04/figures_raw/` 에 보관
- `figures/cross_paper_unified_E4_cdf_E4.png`
- `figures/bootstrap_ci_unified_E4.csv`
- `figures/cross_paper_unified_3env.png`
- `figures/cross_paper_unified_E4_tau_p_actual.png`

설정:

| 항목 | 값 |
| --- | --- |
| AP 수 L | 200 |
| UE 수 K | 50 |
| Antennas/AP N | 8 |
| Carrier | 3 GHz |
| Path loss | 3GPP UMi |
| Channel | one-ring 30 m, Rician K=10 dB |
| tau_c | 150 |
| tau_p_design | 15 |
| MC | 200 setups × 20 channel samples |

E4 main result:

| Scheme | P5 SE | Median SE | Mean SE | Mean vs Random | Mean actual tau_p |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random | 1.149 | 5.036 | 5.291 | 0.00% | 14.94 |
| Gao matching | 1.153 | 5.034 | 5.290 | -0.01% | 15.00 |
| GC (Liu) | 1.169 | 5.034 | 5.292 | +0.02% | 14.98 |
| Structured (Chen) | 1.162 | 5.035 | 5.292 | +0.01% | 14.99 |
| Mussbah | 1.059 | 4.610 | 4.845 | -8.44% | 26.52 |
| TopAP (bisect) | 1.159 | 5.044 | 5.295 | +0.08% | 14.91 |
| H2 Gao+greedy | 1.162 | 5.033 | 5.291 | +0.01% | 15.00 |
| Hybrid#3 | 1.234 | 5.303 | 5.572 | +5.31% | 7.90 |
| Hybrid#4 | 1.161 | 5.032 | 5.292 | +0.01% | 15.00 |

Bootstrap mean SE CI:

| Scheme | Mean SE CI |
| --- | --- |
| Random | 5.291 [5.237, 5.347] |
| Hybrid#3 | 5.572 [5.515, 5.627] |
| Mussbah | 4.845 [4.794, 4.898] |

Seed42 sanity:

- 50 setups × 10 channel samples
- Hybrid#3: +5.30% mean SE vs Random
- Mussbah: -8.12% mean SE vs Random

해석:

- E4 에서 Hybrid#3 가 명확히 1위다.
- Mussbah 는 Random 보다 낮다.
- [Inference] 이유는 actual pilot count 다. Mussbah 는 평균 26.5개의 pilot 을 사용했고,
  Hybrid#3 는 평균 7.9개를 사용했다. E4 의 `tau_p_design=15`와 비교하면 Mussbah 는 overhead
  손실이 커지고, Hybrid#3 는 overhead 이득을 얻는다.

## 9.6 D1/D2 axis decision-level diagnostic — Hybrid 알고리즘 motivation

`Diagnosis.md` 의 핵심 contribution. 단순히 "더 좋은 알고리즘 찾기" 가 아니라 *기존 알고리즘이
무엇을 최적화하는지* decision-level 에서 분리해서 분석했다.

실험 파일: `experiments/diagnose_algorithms.py`. 산출물: `figures/diagnose_algorithms_*.csv`.

핵심 metric 두 개:

| Metric | 정의 | 작을수록 좋음 |
| --- | --- | --- |
| **D1 — Top-N strong-AP collision rate** | 각 UE 의 가장 강하게 들리는 top-N AP 에서 *같은 pilot 사용 UE 수* 평균 | YES |
| **D2 — Coherent pilot interference (per-UE)** | SINR 분모의 same-pilot UE contamination term 의 합 | YES |

50 MC 결과 (Diagnosis.md §4):

| Scheme | D1 (τ_p=10) | D1 (τ_p=20) | D2 (τ_p=10, ×10⁻¹⁹) |
| --- | ---: | ---: | ---: |
| Random | 2.50 | 0.62 | 9.7 |
| Gao matching | **1.59** | 0.68 | 6.81 |
| GC (Liu) | 1.99 | 0.90 | 10.74 |
| Structured (Chen) | 2.41 | **0.16** | 2.99 |

[Inference]:

- *Gao 가 small-τ_p 에서 D1 axis 를 dominate* (1.59 vs 다른 2.0+). 이게 Gao 의 small-τ_p
  advantage 의 *직접 원인*.
- *Structured (Chen) 이 D2 axis 를 dominate* (모든 τ_p 에서 D2 최소). 그러나 throughput 에서는
  small-τ_p 에서 Gao 가 강함 — 즉 *D2 만으로는 small-τ_p 영역 설명 안 됨*.

우리 hybrid 의 motivation:

- **TopAP bisect / Hybrid#3** = D1 axis 를 *element-domain conflict graph* 로 직접 attack.
- **H2 Gao+greedy** = D1 axis (Gao grouping) + D2 axis (greedy contamination-min) 결합.
- **Hybrid#4** = TopAP graph + greedy contam-min 결합.

즉 우리 4가지 hybrid 는 *D1/D2 axis 의 *서로 다른 weighting*. 각 환경에서 어떤 axis 가
dominant 인지에 따라 winner 가 다름.

## 10. 왜 Hybrid#3 가 중요한가

Hybrid#3 는 두 논문의 핵심 아이디어를 선택적으로 결합한다.

| Source | 가져온 아이디어 |
| --- | --- |
| Liu/TopAP diagnosis | strong AP overlap conflict graph |
| Mussbah | adaptive actual pilot count |
| Gao/diagnosis | AP-centric contamination awareness |

결과적으로 Hybrid#3 는 E4 에서:

- 가장 낮은 actual pilot count 를 사용한다.
- 평균 SE 와 P5 모두 Random 보다 높다.
- bootstrap mean SE CI 도 Random 과 분리된다.

### 10.1 Actual pilot count 의 직접 비교

`figures/cross_paper_unified_E4_tau_p_actual.png` 의 정확한 수치 (E4 setting, τ_p_design=15):

| Scheme | actual τ_p mean | actual τ_p min/max | training overhead factor `(150-τ_p)/150` |
| --- | ---: | --- | ---: |
| Hybrid#3 | **7.90** | low | **0.947** (95% data time) |
| Random / Gao / GC / Struct / TopAP / H2 / Hybrid#4 | ~15.0 | ≈ τ_p_design | 0.900 (90% data time) |
| Mussbah | **26.52** | min 22, max 31 | **0.823** (82% data time) |

[Inference] 차이는 명확하다:

- Hybrid#3 의 *fewer pilots* (8 average) → training overhead reduction → SE prefactor +5.2%
  ( = 0.947 / 0.900 - 1 ). 우리 측정 Hybrid#3 +5.31% 와 거의 일치.
- Mussbah 의 *more pilots* (26.5 average) → training overhead 증가 → SE prefactor -8.6%
  ( = 0.823 / 0.900 - 1 ). 우리 측정 Mussbah -8.44% 와 거의 일치.

즉 E4 의 모든 차이는 *actual pilot count 차이* 로 정량 설명된다. SINR improvement 부분의
독립 effect 는 우리 환경에서 명확히 관측되지 않았다.

[Inference] 이 결과는 "beam-domain conflict graph 자체"보다 "더 sparse 하고 적절한 conflict graph
위에 adaptive pilot count 를 얹는 것"이 더 중요할 수 있음을 시사한다.

### 10.2 Hybrid#3 의 sweet spot 과 한계

| 환경 (K) | Hybrid#3 vs Random | 이유 (inferred) |
| --- | ---: | --- |
| K=25 | +5.8% (P5) | TopAP chromatic 작음 → fewer pilots 명확 |
| **K=30 (Mussbah paper)** | **+2.5% (P5)** | sweet spot |
| K=35 | +7.1% (P5) | sweet spot |
| **K=50 (E4)** | **+5.3% (mean)** | sweet spot |
| K=40 | -0.1% (P5) | chromatic 이 τ_p_design 에 근접 → margin 줄어듬 |
| K=45 | -3.5% (P5) | chromatic > τ_p_design → modulo wrap |
| K=200 (stress test) | -0.6% (mean) | chromatic 폭발 → adaptive mechanism 자체가 손해 |

[Inference] Hybrid#3 의 sweet spot 은 *chromatic < τ_p_design* 영역. 즉 *K density 가
충분히 small* 이면 strong, *너무 dense* 면 약함. 이런 K-sensitivity 는 Mussbah 와 같은
*adaptive τ_p mechanism* 의 inherent characteristic.

→ Large K 영역에서는 *non-adaptive* hybrid (TopAP bisect, H2 Gao+greedy, Hybrid#4) 가 더
robust. 즉 *우리 4 hybrid 가 K-envelope 의 서로 다른 영역에서 각자 best*.

## 11. 프로젝트의 진짜 contribution

이 프로젝트의 contribution 은 단순히 "논문 두 개를 실행했다"가 아니다.

실제 contribution:

1. Gao 2024 를 조건부 paper-faithful 수준까지 재현했다.
2. Mussbah 2024 를 multi-antenna channel/SE pipeline 과 함께 구현했다.
3. 두 논문의 antenna mismatch 때문에 direct comparison 이 어렵다는 점을 명확히 드러냈다.
4. E3 stress test 와 E4 common-ground benchmark 로 비교 축을 분리했다.
5. D1/D2 decision-level diagnosis 로 알고리즘이 무엇을 최적화하는지 분석했다.
6. 네 가지 hybrid 알고리즘을 만들었다.
7. E4 에서 Hybrid#3 의 우위를 bootstrap CI 와 actual pilot count diagnostic 으로 설명했다.

## 12. 방어 가능한 주장과 위험한 주장

## 12.1 방어 가능한 주장

- Gao small-pilot advantage 는 재현됐다.
- Mussbah paper-spec 계열 구현은 완료됐지만, default Fig.1 수치 `+8%`는 그대로 재현되지 않았다.
- Mussbah 의 advantage 는 `tau_p_design > chromatic` 조건에서 살아난다.
- E4 common-ground benchmark 에서 Hybrid#3 가 가장 좋다.
- E4 에서 Mussbah 가 낮은 이유는 actual pilot count 가 너무 커지는 것과 관련된다. `[Inference]`
- E4 는 direct paper-original comparison 이 아니라 common-ground algorithm benchmark 다.

## 12.2 위험한 주장

다음 문장은 쓰면 안 된다.

- "두 논문을 완전히 같은 조건에서 공정하게 직접 비교했다."
- "Mussbah 논문의 +8%를 default 조건에서 정확히 재현했다."
- "Hybrid#3 는 모든 환경에서 최고다."
- "Mussbah 알고리즘은 항상 나쁘다."

더 정확한 표현:

- "E1/E2 paper-original reproduce 와 E3/E4 multi-antenna comparison 을 분리해서 보고했다."
- "Hybrid#3 는 small-to-mid K multi-antenna common-ground 환경에서 강했다."
- "Mussbah 는 특정 환경에서는 adaptive pilot mechanism 이 살아나지만, dense 또는 common-ground E4 에서는
  actual pilot count 가 커져 손해를 봤다."

## 13. 실행 방법

## 13.1 테스트

```bash
python -m pytest -q tests/
```

Expected:

```text
21 passed
```

## 13.2 Gao final200

```bash
bash experiments/run_gao_final200.sh
python experiments/summarize_gao_final200.py
```

## 13.3 Mussbah Fig.1 full

```bash
python experiments/mussbah_fig1_full.py \
    --setups 200 --channel-samples 20 \
    --no-progress --out-suffix _200setups_umi
```

## 13.4 E4 unified benchmark

```bash
python experiments/cross_paper_unified_E4.py \
    --setups 200 --channel-samples 20 \
    --out-suffix _E4

python experiments/bootstrap_se_ci.py \
    --input cross_paper_unified_E4_raw_E4.csv \
    --out bootstrap_ci_unified_E4.csv

python experiments/plot_cross_paper_unified_3env.py
python experiments/plot_e4_tau_p_actual.py
```

Cleanup 이후 기존 raw CSV 는 `.artifact_archive/cleanup_2026-06-04/figures_raw/` 에 있다.
위 bootstrap 명령을 기존 raw 로 다시 실행하려면 raw CSV 를 `figures/`로 복사하거나 E4 실험을
다시 실행하면 된다.

## 13.5 Seed42 sanity

```bash
python experiments/cross_paper_unified_E4.py \
    --setups 50 --channel-samples 10 \
    --seed 42 --out-suffix _E4_seed42_50x10

python experiments/bootstrap_se_ci.py \
    --input cross_paper_unified_E4_raw_E4_seed42_50x10.csv \
    --out bootstrap_ci_unified_E4_seed42_50x10.csv
```

## 14. 어떤 파일을 먼저 읽으면 되는가

처음 읽는 순서:

1. `PROJECT_EXPLAINED.md` — 지금 문서.
2. `README.md` — 빠른 요약.
3. `PROGRESS.md` — 현재 상태와 claim boundary.
4. `Defense_summary.md` — 발표/디펜스용 claim.
5. `TUTORIAL.md` — 실행 방법과 코드 walkthrough.
6. `Diagnosis.md` — 왜 hybrid 를 만들었는지.
7. `Mussbah_reproduce_plan.md` — Mussbah 구현/실험 전체 기록.

## 15. 발표에서 보여줄 핵심 그림

추천 figure:

1. `figures/gao_fig3_vs_pilot_number_final200.png`
   - Gao small-pilot advantage.
2. `figures/envelope_tau_p_K30.png`
   - adaptive pilot mechanism 의 enabling condition.
3. `figures/cross_paper_unified_3env.png`
   - E2/E3/E4 비교.
4. `figures/cross_paper_unified_E4_tau_p_actual.png`
   - E4 에서 Hybrid#3 와 Mussbah 가 갈린 직접 원인.
5. `figures/cross_paper_unified_E4_cdf_E4.png`
   - E4 CDF.

## 16. 남은 한계

기술적 한계:

1. **Mussbah Eq.(10)-(14) closed-form 미구현**: 우리는 Monte-Carlo (channel realization +
   empirical SINR averaging) 으로 SE 를 측정했다. Paper 의 closed-form trace term 들과
   *수학적으로 동등* 하지만 *우리 implementation 의 MMSE 가 diagonal approximation* 이므로
   *off-diagonal terms 의 미세 effect* 는 lose. 자세히는 `Mussbah_reproduce_plan.md §18`.
2. **Mussbah Greedy / WGF baseline 미구현**: Paper Fig.1 의 5개 baseline 중 우리는 Random,
   GC (Liu) 만 그대로 포함. Greedy (Ngo 2017) / WGF (Zeng 2021) 는 *paper Fig.1 직접 비교
   상* 빠진 부분.
3. **Gao paper original 의 multi-antenna beam-domain 확장 직접 구현 X**: 현재 E3/E4 의
   Gao matching 은 *element-domain β 만 사용* (multi-antenna 환경에서도 그대로 동작 but beam
   정보 활용 X). 즉 E3/E4 의 Gao 는 paper-original Gao 가 아니라 multi-antenna 환경에 그대로
   이식한 baseline 으로 해석해야 함.
4. **Mussbah paper 의 *DFT codebook size / SNR detection threshold 의 정확한 dB / channel
   covariance fine-tuning*** 의 paper 미명시 detail 의 cumulative effect 가 우리 환경의
   *chromatic 12 vs paper inferred chromatic 3* 차이를 만듬. Default τ_p=10 에서 paper +8%
   claim 정확 재현 X.

방법론적 한계:

1. **E3/E4 는 Gao paper reproduction 이 아님**: Gao paper original 은 N=1 single-antenna.
   E3 (multi-antenna stress test) / E4 (common-ground benchmark) 는 *Gao environment 의
   multi-antenna 확장* — *Gao paper original 과 다른 환경*. 따라서 *Gao paper claim 의
   정량 재현* 으로 부르면 안 된다.
2. **Hybrid#3 의 K-sensitivity**: §10.2 의 결과처럼 K=40 부터 advantage 줄어들고, K=45 에서
   negative. *adaptive τ_p mechanism 의 inherent limitation* — Mussbah 와 같은 한계.
   Cross-paper K-robust 한 우리 algorithm 은 *non-adaptive* (TopAP bisect, H2, Hybrid#4).

운영적 한계:

1. **이 디렉터리는 git repository 가 아니다**. 큰 수정 전에는 version control 또는 백업
   필요.
2. **Statistical confidence**: 우리 bootstrap CI 는 *200 setups × 20 channel samples
   기준*. Mean SE level 은 *대부분 statistically significant* 인데 *P5 level 은 marginal*
   (P5 의 MC variance 크기 때문). 즉 *Mean SE claim 이 더 robust*.
3. **Multi-seed verification 미흡**: Gao reproduce 의 seed=7/42 multi-seed 는 했지만,
   Mussbah / E4 결과는 main seed 만 확정. seed=42 sanity 만 1회 (`bootstrap_ci_unified_E4_seed42_50x10.csv`).
   추가 seed run 으로 더 단단해질 가능성.

## 17. 최종 결론

이 프로젝트는 단순 reproduction 에서 끝나지 않았다. Gao 와 Mussbah 두 논문을 구현하면서,
두 알고리즘이 보는 conflict 구조가 다르다는 점을 진단했고, 그 결과 TopAP 기반 hybrid 들을 만들었다.

가장 중요한 결과는 E4 common-ground benchmark 다. 여기서 Hybrid#3 는 Random 대비 mean SE
`+5.31%`로 통계적으로 분리된 우위를 보였고, Mussbah 원 알고리즘은 `-8.44%`로 낮았다.

[Inference] 이 결과는 "adaptive pilot count" 자체가 좋은 것이 아니라, **어떤 conflict graph 위에서
adaptive pilot count 를 적용하느냐**가 핵심이라는 해석을 가능하게 한다. 이 프로젝트의 새 기여는 바로
그 지점에 있다.
