# Presentation 6-Method Figures

Purpose: final six-method comparison used by the presentation deck.

Simulation setting:

- L = 200 APs
- N = 8 antennas per AP
- K-list = 25 30 35 40 45 50
- tau_c = 150
- baseline/design tau_p = 15
- setups = 200
- carrier = 3 GHz
- power control = full
- weighted beam graph: w_aa = 2, w_ai = 1, w_ia = 1
- Beam-Weighted Threshold uses edge_threshold = 10
- Mussbah Beam Graph uses edge_threshold = 0
- AP-Top-N uses N = 8

Sources:

- base five-method CSV: MJH/result_200_boxplot_ap_domain_env_fixed_with_gao_parallel8/sweep_K_all_schemes.csv
- Mussbah edge-0 CSV: MJH/result_200_boxplot_ap_domain_env_fixed_mussbah_edge0_parallel8/sweep_K_all_schemes.csv
- six-method output CSV: figures/presentation_6method/presentation_mjh_6method_k_sweep.csv

Generated figures:

- presentation_clean_load_crossover_se.png
- presentation_clean_load_crossover_ee.png
- presentation_clean_pilot_count_vs_k.png
- presentation_latest_6method_p5_throughput_vs_k.png
- presentation_latest_6method_ecdf_throughput_k50.png
