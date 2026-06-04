from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
LOGS = ROOT / "logs"
OUT = LOGS / "gao_final200_summary.md"


def mbps(value_bps: float) -> float:
    return float(value_bps) / 1e6


def pct(num: float, den: float) -> float:
    return (float(num) / float(den) - 1.0) * 100.0


def format_table(frame: pd.DataFrame) -> str:
    return frame.to_markdown(index=False, floatfmt=".3f")


def summarize_fig2(lines: list[str]) -> None:
    path = FIGURES / "gao_fig2_cdf_summary_final200.csv"
    if not path.exists():
        lines.append(f"- Missing `{path.relative_to(ROOT)}`")
        return
    df = pd.read_csv(path)
    rows = []
    for power, group in df.groupby("power_control", sort=False):
        vals = dict(zip(group["scheme"], group["p5_mbps"]))
        gao = vals.get("Gao matching")
        random = vals.get("Random")
        graph = vals.get("Graph coloring")
        structured = vals.get("Structured access")
        rows.append(
            {
                "power": power,
                "gao_p5": gao,
                "random_p5": random,
                "graph_p5": graph,
                "structured_p5": structured,
                "gao_vs_random_pct": pct(gao, random),
                "gao_vs_graph_pct": pct(gao, graph),
                "gao_vs_structured_pct": pct(gao, structured),
            }
        )
    lines.append("## Fig.2 P5 summary")
    lines.append("")
    lines.append(format_table(pd.DataFrame(rows)))
    lines.append("")


def summarize_sweep(lines: list[str], filename: str, x_col: str, title: str) -> None:
    path = FIGURES / filename
    if not path.exists():
        lines.append(f"- Missing `{path.relative_to(ROOT)}`")
        return
    df = pd.read_csv(path)
    rows = []
    for (power, x_value), group in df.groupby(["power_control", x_col], sort=False):
        vals = dict(zip(group["scheme"], group["throughput_95_likely_bps"]))
        gao = mbps(vals["Gao matching"])
        random = mbps(vals["Random"])
        graph = mbps(vals["Graph coloring"])
        structured = mbps(vals["Structured access"])
        rows.append(
            {
                "power": power,
                x_col: int(x_value),
                "gao": gao,
                "random": random,
                "graph": graph,
                "structured": structured,
                "gao_vs_random_pct": pct(gao, random),
                "gao_vs_graph_pct": pct(gao, graph),
                "gao_vs_structured_pct": pct(gao, structured),
            }
        )
    lines.append(f"## {title}")
    lines.append("")
    lines.append(format_table(pd.DataFrame(rows)))
    lines.append("")


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    lines = [
        "# Gao final200 summary",
        "",
        "Generated after `experiments/run_gao_final200.sh`.",
        "",
    ]
    summarize_fig2(lines)
    summarize_sweep(lines, "gao_fig3_vs_pilot_number_final200.csv", "tau_p", "Fig.3 sweep")
    summarize_sweep(lines, "gao_fig4_vs_ue_number_final200.csv", "num_ues", "Fig.4 sweep")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
