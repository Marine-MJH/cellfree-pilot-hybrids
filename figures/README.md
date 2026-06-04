# Figures Directory

This directory now keeps only defense-facing figures, summary tables, and bootstrap CI tables.

Archived outputs were moved non-destructively to:

```text
.artifact_archive/cleanup_2026-06-04/
```

Archive contents:

- `figures_raw/`: large per-realization raw CSV files
- `figures_obsolete/`: smoke runs, preliminary variants, superseded plots/tables
- `logs/`: old run logs and stale PID files

Core files to show in a report or defense:

- `gao_fig2_cdf_final200.png`
- `gao_fig3_vs_pilot_number_final200.png`
- `gao_fig4_vs_ue_number_final200.png`
- `mussbah_fig1_full_cdf_200setups_umi.png`
- `mussbah_cdf_tau20_paperstyle.png`
- `envelope_tau_p_K30.png`
- `envelope_K_tau10.png`
- `envelope_advantage_vs_random.png`
- `cross_paper_full_final.png`
- `cross_paper_unified_3env.png`
- `cross_paper_unified_E4_cdf_E4.png`
- `cross_paper_unified_E4_key_cdf_E4.png`
- `cross_paper_unified_E4_effect_decomposition.png`
- `cross_paper_unified_E4_tau_p_actual.png`
- `two_by_two_gao_mussbah_matrix.png`
- `two_by_two_gao_mussbah_matrix.csv`

If a bootstrap command needs a raw CSV that is no longer in this directory, either rerun the
corresponding experiment or copy the needed raw CSV back from the archive.
