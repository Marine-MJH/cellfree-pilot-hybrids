# Current Progress

Last updated: 2026-06-04

This file is the current handoff snapshot for a teammate. It is not a full
lab notebook. For the full beginner-friendly explanation, start with
`PROJECT_EXPLAINED.md`.

## 1. Executive Status

| Area | Status | Evidence / file |
| --- | --- | --- |
| Repository cleanup | Ready for teammate review | `README.md`, `.gitignore`, `figures/README.md` |
| Tests | Passing | `python -m pytest -q tests/` -> `21 passed` |
| Gao 2024 reproduction | Conditional paper-faithful | `figures/gao_*_final200.*`, `logs/gao_final200_summary.md` |
| Mussbah 2024 implementation | Paper-spec pipeline implemented, exact +8% claim not reproduced | `src/mussbah_*.py`, `experiments/mussbah_fig1_full.py` |
| Hybrid algorithms | Implemented and benchmarked | `src/pilot_schemes/`, `Diagnosis.md` |
| Unified E4 benchmark | Completed | `figures/cross_paper_unified_E4_*`, `figures/bootstrap_ci_unified_E4.csv` |

Bottom line:

- Gao's strongest paper-relevant claim, small-pilot gain over Random, is
  reproduced closely in the comparable setting.
- Gao does not dominate the Liu/Chen benchmarks across the full reproduced
  sweep when those baselines are implemented strongly.
- Mussbah's algorithm and channel/SE pipeline are implemented, but its paper
  Fig. 1 `+8%` advantage is not reproduced under the literal/default settings
  used here.
- Hybrid#3 is the strongest result in the E4 common-ground benchmark because it
  keeps the actual number of pilots low while using a sparse TopAP conflict
  graph.

## 2. What Is Implemented

Core simulation code:

| Component | File |
| --- | --- |
| Simulation config | `src/config.py` |
| AP/UE topology, path loss, beam powers | `src/network.py` |
| Gao/Ngo single-antenna channel-estimation variance | `src/channel.py` |
| SINR, throughput, CDF, P5 metric | `src/metrics.py` |
| Full / fractional / max-min power control | `src/power_control.py` |
| 3GPP UMi path loss | `src/pathloss_umi.py` |
| Mussbah one-ring/Rician channel model | `src/mussbah_channel.py` |
| Mussbah-style Monte-Carlo SE | `src/mussbah_se.py` |

Pilot assignment schemes:

| Scheme | File |
| --- | --- |
| Random | `src/pilot_schemes/random_scheme.py` |
| Gao matching | `src/pilot_schemes/matching_gao.py` |
| Liu graph coloring | `src/pilot_schemes/graph_coloring.py` |
| Chen structured access | `src/pilot_schemes/structured_access.py` |
| Mussbah beam-domain DSATUR | `src/pilot_schemes/beam_domain_mussbah.py` |
| TopAP graph coloring | `src/pilot_schemes/top_ap_graph.py` |
| H2 Gao+greedy | `src/pilot_schemes/matching_greedy_h2.py` |
| Hybrid#3 / Hybrid#4 | `src/pilot_schemes/top_ap_graph.py`, `src/pilot_schemes/hybrid4_topap_greedy.py` |

## 3. Results Snapshot

### 3.1 Gao Reproduction

Final Gao artifacts:

- `figures/gao_fig2_cdf_final200.png`
- `figures/gao_fig3_vs_pilot_number_final200.png`
- `figures/gao_fig4_vs_ue_number_final200.png`
- `logs/gao_final200_summary.md`

Main result:

| Setting | Paper-level comparison | This project |
| --- | ---: | ---: |
| `tau_p=10`, max-min power, Gao vs Random | about `+23%` | `+21.7%` |

Important caveat:

At the default Fig. 2 point, `M=200`, `K=500`, `tau_p=20`, Gao is consistently
above Random, but not consistently above the Liu/Chen baselines:

| Power control | Gao vs Random | Gao vs Graph | Gao vs Structured |
| --- | ---: | ---: | ---: |
| Fractional | `+8.0%` | `+0.3%` | `-3.0%` |
| Full | `+7.8%` | `+1.8%` | `-2.6%` |
| Max-min | `+15.5%` | `-3.0%` | `-5.2%` |

Interpretation:

- The small-pilot mechanism is credible.
- The broad claim "Gao beats all benchmarks everywhere" should not be used.
- Gao matching is evaluated mostly as pilot assignment; all-AP serving is the
  default convention in the final runs.

### 3.2 Mussbah Reproduction

Implemented:

- 3GPP UMi path loss
- one-ring angular spread model
- Rician channel model
- active beam selection
- beam-domain DSATUR pilot coloring
- Monte-Carlo SE pipeline

Not reproduced:

- Mussbah Fig. 1's reported `+8%` advantage under the literal/default
  interpretation used here.

Main diagnosis:

- Mussbah's advantage depends heavily on whether adaptive coloring uses fewer
  pilots than the design budget.
- In our default UMi setting, Mussbah's conflict graph is not sparse enough, so
  the actual pilot count becomes too high and training overhead dominates.

### 3.3 E4 Unified Benchmark

E4 is a common-ground benchmark, not a paper-original environment.

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

Headline E4 result:

| Scheme | P5 SE | Mean SE | Mean vs Random | Mean actual pilots |
| --- | ---: | ---: | ---: | ---: |
| Random | 1.149 | 5.291 | 0.00% | 14.94 |
| Mussbah | 1.059 | 4.845 | -8.44% | 26.52 |
| Hybrid#3 | 1.234 | 5.572 | +5.31% | 7.90 |

Bootstrap mean SE 95% CI:

| Scheme | Mean SE 95% CI |
| --- | --- |
| Random | 5.291 [5.237, 5.347] |
| Mussbah | 4.845 [4.794, 4.898] |
| Hybrid#3 | 5.572 [5.515, 5.627] |

Interpretation:

- Hybrid#3 wins E4 because its TopAP graph is sparse enough to use fewer actual
  pilots. A fixed-`tau_p_length=15` sanity check reduced the large mean-SE gap
  to about `+0.07%`, so the headline E4 gain should be interpreted as adaptive
  training-overhead reduction, not as a large fixed-budget SINR gain.
- Mussbah loses E4 because the beam-domain conflict graph becomes too dense in
  this environment, increasing actual pilot count and reducing the prelog factor.

Readable E4 figures:

- `figures/cross_paper_unified_E4_key_cdf_E4.png`: Random / Mussbah / Hybrid#3
  only, for slide readability.
- `figures/cross_paper_unified_E4_effect_decomposition.png`: mean SE shift next
  to actual pilot count; this is the safer main figure for E4.

### 3.4 Gao/Mussbah 2x2 Sanity Matrix

Question checked: can we evaluate Gao and Mussbah in both the single-antenna
Gao environment and the multi-antenna Mussbah environment?

Answer:

| Algorithm / environment | E1: Gao N=1 paper env | E2: Mussbah N=8 paper env |
| --- | --- | --- |
| Gao matching | Paper-faithful; `+3.66%` mean Mbps vs Random in 50-MC sanity | Transplant baseline; `+0.04%` mean SE vs Random in existing E2 result |
| Mussbah | Not paper-faithful in N=1. Forced adaptive variant used `134.3` pilots on average and collapsed to `-59.4%` mean Mbps vs Random. Forced clipped variant was near Random (`+0.66%`). | Paper-environment algorithm; `-2.23%` mean SE vs Random in existing E2 result |

Artifacts:

- `figures/two_by_two_gao_mussbah_matrix.csv`
- `figures/two_by_two_gao_mussbah_matrix.png`

Interpretation:

- A strict paper-faithful 2x2 matrix is impossible because Mussbah requires
  multi-antenna beam-domain information while Gao's original environment is
  single-antenna.
- The off-diagonal Gao-in-N=8 cell is a reasonable algorithm transplant because
  Gao only needs AP-level large-scale gain.
- The off-diagonal Mussbah-in-N=1 cell is a forced/degenerate variant. It should
  only be used to explain why a strict 2x2 is not meaningful.

## 4. What To Tell A Teammate

Safe claims:

- The codebase contains a working pilot-assignment benchmark suite for
  cell-free massive MIMO.
- Gao, Liu, Chen, Mussbah, Random, and four hybrid schemes are implemented under
  one Python interface.
- Gao's small-pilot gain over Random is reproduced closely.
- Mussbah's adaptive-pilot mechanism is implemented, but its exact paper Fig. 1
  numeric gain is not reproduced in the default setting.
- Hybrid#3 is the strongest E4 common-ground result among the tested schemes,
  mainly because it uses fewer actual pilots and therefore lower training
  overhead.

Do not claim:

- "Gao is fully reproduced in every figure and benchmark ordering."
- "Mussbah's `+8%` paper claim is exactly reproduced."
- "E4 proves one algorithm is universally best."
- "Hybrid#3 has a large fixed-budget SINR advantage in E4."
- "The Mussbah SE code is a line-by-line closed-form implementation of every
  trace term in Eq. (10)-(14)."

## 5. Recommended Reading Order

For a teammate who has not seen the project:

1. `README.md` for the GitHub-facing summary.
2. `PROJECT_EXPLAINED.md` for the conceptual walkthrough.
3. `PROGRESS.md` for the current status and honest result boundaries.
4. `Defense_summary.md` for presentation-ready claims and FAQ.
5. `TUTORIAL.md` for commands and code walkthrough.
6. `Diagnosis.md` for the hybrid-algorithm motivation.
7. `Mussbah_reproduce_plan.md` only if they need the long Mussbah experiment log.

## 6. Reproduction Commands

Install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Test:

```bash
python -m pytest -q tests/
```

Gao final summaries:

```bash
bash experiments/run_gao_final200.sh
python experiments/summarize_gao_final200.py
```

Mussbah full run:

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
```

If raw CSVs are missing, rerun the relevant experiment. Raw Monte-Carlo CSVs and
obsolete intermediate outputs are intentionally kept out of git.
