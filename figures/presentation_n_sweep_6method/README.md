# N-Sweep 6-Method Presentation Figures

Purpose: keep the presentation_6method setting fixed, hold K=50, and sweep AP antenna count N from 1 to 8.

Simulation setting:

- L = 200 APs
- K = 50 UEs
- N-list = 1 2 3 4 5 6 7 8
- eCDF N = 8
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

- n_sweep_6method_summary.csv
- n_sweep_6method_ecdf_raw.csv
- n_sweep_avg_se_vs_n.png
- n_sweep_avg_ee_vs_n.png
- n_sweep_pilot_count_vs_n.png
- n_sweep_p5_throughput_vs_n.png
- n_sweep_ecdf_throughput.png
