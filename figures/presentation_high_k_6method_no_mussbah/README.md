# High-K 5-Method Figures Without Mussbah

Purpose: replot the existing high-K results after removing Mussbah Beam Graph, whose pilot count exceeds the coherence block at high K and compresses the y-axis.

No simulation was rerun for this directory. These plots are generated from:

- figures/presentation_high_k_6method/high_k_6method_summary.csv
- figures/presentation_high_k_6method/high_k_6method_ecdf_raw.csv

Included methods:

- Random
- Gao Matching
- AP-Top-N (N=8)
- Beam-Weighted Threshold
- Beam-Resource Matching

K-list = 50 100 150 200 250 300

Inherited source setting:

# High-K 6-Method Presentation Figures

Purpose: keep the presentation_6method setting fixed and increase only K to test whether Gao Matching separates from Random under heavier user load.

Simulation setting:

- L = 200 APs
- N = 8 antennas per AP
- K-list = 50 100 150 200 250 300
- eCDF K = 300
- tau_c = 150
- baseline/design tau_p = 15
- setups = 200
- workers = 8
- carrier = 3.0 GHz
- beam_detect_snr_db = 0.0
- power_control = full
- power_model = ref12-rf
- fronthaul_mode = active_users
- weighted graph weights: w_aa = 2.0, w_ai = 1.0, w_ia = 1.0
- Beam-Weighted Threshold edge_threshold = 10.0
- Mussbah Beam Graph edge_threshold = 0.0
- matching_resource_quota = 0 (0 means baseline tau_p)
- seed = 7

Methods:

- Random
- Gao Matching
- Mussbah Beam Graph
- AP-Top-N (N=8)
- Beam-Weighted Threshold
- Beam-Resource Matching

Outputs:

- high_k_6method_summary.csv
- high_k_6method_ecdf_raw.csv
- high_k_avg_se_vs_k.png
- high_k_avg_ee_vs_k.png
- high_k_pilot_count_vs_k.png
- high_k_p5_throughput_vs_k.png
- high_k_ecdf_throughput.png
