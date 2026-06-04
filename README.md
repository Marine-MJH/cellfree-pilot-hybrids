# Cell-Free Massive MIMO Pilot Assignment Benchmark

Reproduction and cross-environment benchmarking code for pilot assignment in
cell-free massive MIMO networks.

This repository reproduces and compares ideas from:

- Gao et al., *A Matching-Based Pilot Assignment Algorithm for Cell-Free Massive MIMO Networks*, IEEE TVT 2024
- Mussbah et al., *Beam-Domain-Based Pilot Assignment for Energy Efficient Cell-Free Massive MIMO*, IEEE CL 2024

It also implements four hybrid pilot assignment algorithms built from the
diagnosed strengths and weaknesses of the paper methods.

## What This Project Does

Pilot assignment matters because multiple users often reuse the same pilot
sequence. Bad reuse contaminates channel estimates and degrades spectral
efficiency, especially for weak users.

This project:

- Reproduces Gao-style single-antenna cell-free MIMO experiments.
- Implements a Mussbah-style multi-antenna beam-domain channel and SE pipeline.
- Compares Gao, Liu, Chen, Mussbah, Random, and four hybrid schemes.
- Separates paper-original reproduction from cross-paper benchmarking, because
  Gao assumes single-antenna APs while Mussbah assumes multi-antenna APs.
- Adds an E4 common-ground benchmark where all nine schemes run under the same
  multi-antenna environment.

For a detailed beginner-friendly walkthrough, read
[PROJECT_EXPLAINED.md](PROJECT_EXPLAINED.md).

## Key Results

### Gao Reproduction

Gao's small-pilot advantage is reproduced in the strongest comparable region:

| Setting | Result |
| --- | --- |
| `tau_p=10`, max-min power | Gao vs Random: `+21.7%` |
| Paper claim | about `+23%` |

Source: [logs/gao_final200_summary.md](logs/gao_final200_summary.md)

### Mussbah Reproduction

The Mussbah algorithm, 3GPP UMi path loss, one-ring/Rician channel model, active
beam sets, and Monte-Carlo SE pipeline are implemented. The exact paper Fig. 1
`+8%` claim is not reproduced under the literal/default interpretation used here.

The main finding is that Mussbah's advantage depends on whether its adaptive
coloring uses fewer pilots than the design budget. When the actual pilot count
is too high, training overhead dominates.

### E4 Unified Benchmark

E4 is a common-ground multi-antenna benchmark. It is not a paper-original
environment.

| Parameter | Value |
| --- | --- |
| APs | `L=200` |
| UEs | `K=50` |
| Antennas/AP | `N=8` |
| Carrier | `3 GHz` |
| Channel | 3GPP UMi + one-ring 30 m + Rician 10 dB |
| Coherence block | `tau_c=150` |
| Pilot design budget | `tau_p_design=15` |
| Monte Carlo | 200 setups x 20 channel samples |

E4 result:

| Scheme | P5 SE | Mean SE | Mean vs Random | Mean actual pilots |
| --- | ---: | ---: | ---: | ---: |
| Random | 1.149 | 5.291 | 0.00% | 14.94 |
| Mussbah | 1.059 | 4.845 | -8.44% | 26.52 |
| Hybrid#3 | **1.234** | **5.572** | **+5.31%** | **7.90** |

Bootstrap mean SE CI:

| Scheme | Mean SE 95% CI |
| --- | --- |
| Random | 5.291 [5.237, 5.347] |
| Mussbah | 4.845 [4.794, 4.898] |
| Hybrid#3 | 5.572 [5.515, 5.627] |

The actual-pilot-count diagnostic shows why Hybrid#3 wins in E4 while Mussbah
loses: Hybrid#3 colors a much sparser conflict graph.

## Important Figures

| Figure | Purpose |
| --- | --- |
| [gao_fig3_vs_pilot_number_final200.png](figures/gao_fig3_vs_pilot_number_final200.png) | Gao pilot-length sweep |
| [mussbah_fig1_full_cdf_200setups_umi.png](figures/mussbah_fig1_full_cdf_200setups_umi.png) | Mussbah Fig. 1 style CDF |
| [envelope_tau_p_K30.png](figures/envelope_tau_p_K30.png) | Adaptive-pilot enabling condition |
| [envelope_K_tau10.png](figures/envelope_K_tau10.png) | K-sensitivity envelope |
| [cross_paper_full_final.png](figures/cross_paper_full_final.png) | Multi-antenna stress test |
| [cross_paper_unified_3env.png](figures/cross_paper_unified_3env.png) | E2/E3/E4 comparison |
| [cross_paper_unified_E4_tau_p_actual.png](figures/cross_paper_unified_E4_tau_p_actual.png) | E4 actual pilot count diagnostic |

## Algorithms

Implemented paper and baseline schemes:

- Random pilot assignment
- Gao matching-based assignment
- Liu graph coloring
- Chen structured access
- Mussbah beam-domain Dsatur coloring
- Upper-bound/reference assignment

Implemented hybrid schemes:

- **TopAP (bisect)**: top-N strongest AP overlap graph + coloring
- **H2 Gao+greedy**: Gao grouping + contamination-minimizing greedy coloring
- **Hybrid#3 (TopAP N=8 adaptive)**: TopAP conflict graph + Mussbah-style adaptive pilot count
- **Hybrid#4 (TopAP+greedy)**: TopAP conflict graph + greedy contamination minimization

## Repository Layout

```text
src/
  config.py                  # Shared simulation parameters
  network.py                 # AP/UE topology, path loss, beam powers, beam_info
  channel.py                 # Gao/Ngo channel-estimation variance
  metrics.py                 # SINR, throughput, CDF/P5 metrics
  power_control.py           # Full, fractional, max-min power control
  pathloss_umi.py            # 3GPP UMi path loss and LoS/NLoS
  mussbah_channel.py         # One-ring + Rician channel model
  mussbah_se.py              # Mussbah-style Monte-Carlo SE
  pilot_schemes/             # All pilot assignment algorithms

experiments/
  fig2_cdf.py
  fig3_vs_pilot_number.py
  fig4_vs_ue_number.py
  mussbah_fig1_full.py
  mussbah_fig3_k_sweep.py
  cross_paper_full.py
  cross_paper_unified_E4.py
  plot_cross_paper_unified_3env.py
  plot_e4_tau_p_actual.py
  bootstrap_se_ci.py

figures/
  README.md                  # Figure/archive policy
  *.png, *.csv               # Core report-facing plots and summary tables

tests/
  test_*.py
```

Raw Monte-Carlo CSVs and obsolete intermediate outputs are kept out of git.
Locally, they were archived under `.artifact_archive/cleanup_2026-06-04/`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Tests

```bash
python -m pytest -q tests/
```

Expected:

```text
21 passed
```

## Reproduce Selected Experiments

Gao final summaries:

```bash
bash experiments/run_gao_final200.sh
python experiments/summarize_gao_final200.py
```

Mussbah full MC:

```bash
python experiments/mussbah_fig1_full.py \
  --setups 200 --channel-samples 20 \
  --no-progress --out-suffix _200setups_umi
```

E4 unified benchmark:

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

If the raw CSV is not in `figures/`, rerun the experiment. In the local cleanup
snapshot, old raw CSVs are under `.artifact_archive/cleanup_2026-06-04/figures_raw/`,
but that archive is intentionally ignored by git.

## Limitations

- Gao and Mussbah are not directly comparable under their original paper
  environments because their antenna models differ.
- The E3/E4 results are multi-antenna comparison benchmarks, not Gao
  paper-original reproductions.
- The Mussbah SE implementation uses a Monte-Carlo pipeline with a diagonal
  beam-domain MMSE approximation; it is not a line-by-line closed-form
  implementation of every trace term in Mussbah Eq. (10)-(14).
- Mussbah's reported `+8%` Fig. 1 advantage is not reproduced under the default
  literal interpretation used here.
- Hybrid#3 is strong in E4 and small-to-mid K regimes, but it is not claimed to
  dominate every environment.

## Documentation

- [PROJECT_EXPLAINED.md](PROJECT_EXPLAINED.md): full beginner-friendly explanation
- [Defense_summary.md](Defense_summary.md): defense-ready summary and FAQ
- [PROGRESS.md](PROGRESS.md): Gao reproduction details
- [Mussbah_reproduce_plan.md](Mussbah_reproduce_plan.md): Mussbah reproduction and E4 details
- [Diagnosis.md](Diagnosis.md): D1/D2 algorithm diagnostics and hybrid motivation
- [TUTORIAL.md](TUTORIAL.md): command-oriented walkthrough

## Citation

If you use this code, cite the original papers listed above. A formal citation
file is not included yet.
