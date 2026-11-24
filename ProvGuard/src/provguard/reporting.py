"""Aggregate trial logs into LaTeX tables (tab_asr.tex, tab_utility.tex) and PDF figures (Tier 7 - C22, C23, C24)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io import write_json
from .metrics import (
    binder_false_reject_rate,
    false_block_rate,
    latency_summary,
    sink_coverage,
    task_success_rate,
)
from .statistics import binomial_pass_probability, mcnemar_exact_pvalue, wilson_interval

_CHANNEL_LABELS: dict[str, str] = {
    "hidden": "Hidden / low-contrast (C5)",
    "overlay": "Cross-app overlays (C4)",
    "notif": "Notifications (C3)",
    "rebinding": "Foreground rebinding (C8)",
}

_CONFIG_DISPLAY: dict[str, str] = {
    "B0": "B0 (No defense)",
    "B1": "B1 (Spotlighting)",
    "B2": "B2 (Def.\\ prompt)",
    "labels": "PG-L (Labels only)",
    "gate": "PG-G (Gate only)",
    "binder": "PG-B (Binding only)",
    "no_perc": "PG $-$perc",
    "full": "PG (Full system)",
}


def load_trial_rows(trials_path: str | Path) -> list[dict[str, Any]]:
    path = Path(trials_path)
    if path.is_dir():
        path = path / "trials.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Trials file not found: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _rate_and_ci(successes: int, total: int) -> dict[str, Any]:
    if total == 0:
        return {"count": 0, "total": 0, "rate": 0.0, "pct": 0.0, "ci95_pct": [0.0, 0.0]}
    rate = successes / total
    interval = wilson_interval(successes, total)
    return {
        "count": successes,
        "total": total,
        "rate": round(rate, 4),
        "pct": round(rate * 100.0, 1),
        "ci95_pct": [round(interval.lower * 100.0, 1), round(interval.upper * 100.0, 1)],
    }


def compute_table_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-channel ASR, Wilson CIs, McNemar p-values, FBR, TSR, and latency."""

    present_configs = []
    for preferred in ("B0", "B1", "B2", "labels", "gate", "binder", "no_perc", "full"):
        if any(r.get("config") == preferred for r in rows):
            present_configs.append(preferred)
    for other in sorted({str(r.get("config")) for r in rows}):
        if other not in present_configs:
            present_configs.append(other)

    present_channels = []
    for ch in ("hidden", "overlay", "notif", "rebinding"):
        if any(r.get("channel") == ch and r.get("trial_type") == "attack" for r in rows):
            present_channels.append(ch)
    for other_ch in sorted(
        {str(r.get("channel")) for r in rows if r.get("trial_type") == "attack"}
    ):
        if other_ch not in present_channels:
            present_channels.append(other_ch)

    asr_table: dict[str, dict[str, Any]] = {}
    for ch in present_channels:
        asr_table[ch] = {}
        for cfg in present_configs:
            subset = [
                r
                for r in rows
                if r.get("trial_type") == "attack"
                and r.get("channel") == ch
                and r.get("config") == cfg
            ]
            succ = sum(1 for r in subset if r.get("adversarial_success"))
            asr_table[ch][cfg] = _rate_and_ci(succ, len(subset))

    # Pooled attack ASR across all attack channels
    pooled_asr: dict[str, Any] = {}
    for cfg in present_configs:
        subset = [
            r for r in rows if r.get("trial_type") == "attack" and r.get("config") == cfg
        ]
        succ = sum(1 for r in subset if r.get("adversarial_success"))
        pooled_asr[cfg] = _rate_and_ci(succ, len(subset))

    # Paired McNemar exact test comparing each baseline against 'full' on attack cases
    mcnemar_vs_full: dict[str, float] = {}
    if "full" in present_configs:
        full_by_key = {
            (str(r.get("case")), int(r.get("rep", 1))): bool(r.get("adversarial_success"))
            for r in rows
            if r.get("trial_type") == "attack" and r.get("config") == "full"
        }
        for cfg in present_configs:
            if cfg == "full":
                continue
            b_only = 0
            c_only = 0
            for r in rows:
                if r.get("trial_type") != "attack" or r.get("config") != cfg:
                    continue
                key = (str(r.get("case")), int(r.get("rep", 1)))
                if key not in full_by_key:
                    continue
                base_succ = bool(r.get("adversarial_success"))
                full_succ = full_by_key[key]
                if base_succ and not full_succ:
                    b_only += 1
                elif not base_succ and full_succ:
                    c_only += 1
            mcnemar_vs_full[cfg] = round(mcnemar_exact_pvalue(b_only, c_only), 6)

    # Utility & Overhead per configuration
    utility_table: dict[str, dict[str, Any]] = {}
    for cfg in present_configs:
        cfg_rows = [r for r in rows if r.get("config") == cfg]
        benign_rows = [r for r in cfg_rows if r.get("trial_type") == "benign"]
        protected_benign = [r for r in benign_rows if r.get("protected")]

        tsr_val = task_success_rate(benign_rows) if benign_rows else 1.0
        fbr_val = false_block_rate(benign_rows) if protected_benign else 0.0
        bfr_val = binder_false_reject_rate(benign_rows) if benign_rows else 0.0
        sink_target_rows = [
            r
            for r in cfg_rows
            if (r.get("trial_type") == "benign" and r.get("ground_truth_protected"))
            or (
                r.get("trial_type") == "attack"
                and (
                    bool(r.get("protected"))
                    or (
                        r.get("suite") != "attackkit"
                        and bool(r.get("ground_truth_protected"))
                    )
                    or (r.get("proposed_action") or {}).get("target_region_id")
                    in {"r0.9", "r0.8", "r0.7", "r0.2"}
                )
            )
        ]
        cov_val = sink_coverage(sink_target_rows) if sink_target_rows else 1.0

        latencies = [float(r.get("latency_ms", 0.0)) for r in cfg_rows]
        lat_stats = latency_summary(latencies) if latencies else {"p50_ms": 0.0, "p95_ms": 0.0}
        tokens = [int(r.get("total_tokens", 0)) for r in cfg_rows]
        mean_tokens = sum(tokens) / len(tokens) if tokens else 0.0

        completed_cnt = sum(1 for r in benign_rows if r.get("task_completed"))
        fblock_cnt = sum(
            1
            for r in protected_benign
            if r.get("gate_decision") == "escalate" or r.get("dispatch_status") == "reobserve"
        )
        utility_table[cfg] = {
            "tsr": _rate_and_ci(completed_cnt, len(benign_rows)),
            "fbr": _rate_and_ci(fblock_cnt, len(protected_benign)),
            "tsr_pct": round(tsr_val * 100.0, 1),
            "fbr_pct": round(fbr_val * 100.0, 1),
            "binder_false_reject_pct": round(bfr_val * 100.0, 1),
            "sink_coverage_pct": round(cov_val * 100.0, 1),
            "latency_p50_ms": round(lat_stats["p50_ms"], 2),
            "latency_p95_ms": round(lat_stats["p95_ms"], 2),
            "mean_tokens": round(mean_tokens, 1),
        }

    return {
        "total_trials": len(rows),
        "configs": present_configs,
        "channels": present_channels,
        "asr_by_channel": asr_table,
        "pooled_asr": pooled_asr,
        "mcnemar_pvalue_vs_full": mcnemar_vs_full,
        "utility_by_config": utility_table,
    }


def render_tab_asr_tex(metrics: dict[str, Any]) -> str:
    """Render Table 8 (tab_asr.tex) in booktabs LaTeX format without hard-coded numbers."""

    configs: list[str] = metrics["configs"]
    channels: list[str] = metrics["channels"]
    col_spec = "@{}l " + " ".join("c" for _ in configs) + "@{}"
    headers = " & ".join(_CONFIG_DISPLAY.get(c, c) for c in configs)

    lines = [
        "% Auto-generated by scripts/make_tables.py from trials.jsonl. Do not edit by hand.",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Attack success rate (\\%) with 95\\% Wilson confidence intervals per channel and configuration.}",
        "\\label{tab:res-asr}",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4.5pt}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\toprule",
        f"Attack Channel & {headers} \\\\",
        "\\midrule",
    ]

    for ch in channels:
        ch_label = _CHANNEL_LABELS.get(ch, ch.replace("_", " ").title())
        cells: list[str] = []
        for cfg in configs:
            entry = metrics["asr_by_channel"][ch][cfg]
            lo, hi = entry["ci95_pct"]
            cells.append(f"{entry['pct']:.1f} ({lo:.1f}--{hi:.1f})")
        lines.append(f"{ch_label} & {' & '.join(cells)} \\\\")

    lines.append("\\midrule")
    pooled_cells: list[str] = []
    for cfg in configs:
        entry = metrics["pooled_asr"][cfg]
        lo, hi = entry["ci95_pct"]
        pooled_cells.append(f"\\textbf{{{entry['pct']:.1f}}} ({lo:.1f}--{hi:.1f})")
    lines.append(f"\\textbf{{Pooled Attack ASR}} & {' & '.join(pooled_cells)} \\\\")

    if metrics.get("mcnemar_pvalue_vs_full"):
        p_cells: list[str] = []
        for cfg in configs:
            if cfg == "full":
                p_cells.append("--")
            else:
                pval = metrics["mcnemar_pvalue_vs_full"].get(cfg, 1.0)
                p_cells.append("$<0.0001$" if pval < 0.0001 else f"${pval:.4f}$")
        lines.append(f"McNemar $p$-value vs.\\ PG & {' & '.join(p_cells)} \\\\")

    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def render_tab_utility_tex(metrics: dict[str, Any]) -> str:
    """Render Table 9 (tab_utility.tex) in booktabs LaTeX format."""

    configs: list[str] = metrics["configs"]
    lines = [
        "% Auto-generated by scripts/make_tables.py from trials.jsonl. Do not edit by hand.",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Benign utility, false block rate, sink coverage, and per-step overhead across configurations.}",
        "\\label{tab:res-utility}",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4.5pt}",
        "\\begin{tabular}{@{}l c c c c c c@{}}",
        "\\toprule",
        "Configuration & TSR (\\%) & FBR (\\%) & Binder Reject (\\%) & Sink Cov.\\ (\\%) & Latency p50 / p95 (ms) & Mean Tokens \\\\",
        "\\midrule",
    ]

    for cfg in configs:
        u = metrics["utility_by_config"][cfg]
        tsr_lo, tsr_hi = u["tsr"]["ci95_pct"]
        fbr_lo, fbr_hi = u["fbr"]["ci95_pct"]
        disp_name = _CONFIG_DISPLAY.get(cfg, cfg)
        lines.append(
            f"{disp_name} & "
            f"{u['tsr_pct']:.1f} ({tsr_lo:.1f}--{tsr_hi:.1f}) & "
            f"{u['fbr_pct']:.1f} ({fbr_lo:.1f}--{fbr_hi:.1f}) & "
            f"{u['binder_false_reject_pct']:.1f} & "
            f"{u['sink_coverage_pct']:.1f} & "
            f"{u['latency_p50_ms']:.2f} / {u['latency_p95_ms']:.2f} & "
            f"{u['mean_tokens']:.1f} \\\\"
        )

    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def generate_tables(
    trials_path: str | Path,
    out_dir: str | Path,
    *,
    sections_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Generate tab_asr.tex, tab_utility.tex, and summary_metrics.json from trials.jsonl."""

    rows = load_trial_rows(trials_path)
    metrics = compute_table_metrics(rows)
    tab_asr = render_tab_asr_tex(metrics)
    tab_utility = render_tab_utility_tex(metrics)

    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    asr_file = dest / "tab_asr.tex"
    util_file = dest / "tab_utility.tex"
    json_file = dest / "summary_metrics.json"

    asr_file.write_text(tab_asr, encoding="utf-8")
    util_file.write_text(tab_utility, encoding="utf-8")
    write_json(json_file, metrics)

    written = [str(asr_file), str(util_file), str(json_file)]
    if sections_dir is not None:
        sec_dest = Path(sections_dir)
        sec_dest.mkdir(parents=True, exist_ok=True)
        (sec_dest / "tab_asr.tex").write_text(tab_asr, encoding="utf-8")
        (sec_dest / "tab_utility.tex").write_text(tab_utility, encoding="utf-8")
        written.extend([str(sec_dest / "tab_asr.tex"), str(sec_dest / "tab_utility.tex")])

    return {
        "total_trials": metrics["total_trials"],
        "files_written": written,
        "pooled_asr": {k: v["pct"] for k, v in metrics["pooled_asr"].items()},
        "fbr": {k: v["fbr_pct"] for k, v in metrics["utility_by_config"].items()},
        "tsr": {k: v["tsr_pct"] for k, v in metrics["utility_by_config"].items()},
    }


def generate_figures(
    trials_path: str | Path,
    out_dir: str | Path,
) -> list[str]:
    """Generate 3 publication PDF + PNG figures from trials.jsonl (Tier 7 - C23)."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows = load_trial_rows(trials_path)
    metrics = compute_table_metrics(rows)
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    configs: list[str] = metrics["configs"]
    channels: list[str] = metrics["channels"]

    # 1. Figure 1: Attack Success Rate (%) by Channel & Configuration
    fig1, ax1 = plt.subplots(figsize=(7.5, 4.0))
    x = np.arange(len(channels))
    width = 0.8 / max(1, len(configs))
    colors = ["#c0392b", "#e67e22", "#2980b9", "#27ae60"]

    for idx, cfg in enumerate(configs):
        vals = [metrics["asr_by_channel"][ch][cfg]["pct"] for ch in channels]
        offset = (idx - (len(configs) - 1) / 2.0) * width
        ax1.bar(
            x + offset,
            vals,
            width=width * 0.92,
            label=_CONFIG_DISPLAY.get(cfg, cfg),
            color=colors[idx % len(colors)],
        )

    ax1.set_xticks(x)
    ax1.set_xticklabels([c.capitalize() for c in channels])
    ax1.set_ylabel("Attack Success Rate (%)")
    ax1.set_ylim(0, 112)
    ax1.set_title("Attack Success Rate by Channel and Defense Configuration", pad=28)
    ax1.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=min(4, max(1, len(configs))),
        frameon=True,
        fontsize=8.5,
    )
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    fig1.tight_layout()
    for ext in ("pdf", "png"):
        p = dest / f"fig_asr_by_channel.{ext}"
        fig1.savefig(p, dpi=200)
        written.append(str(p))
    plt.close(fig1)

    # 2. Figure 2: Pooled ASR vs Benign TSR / FBR Ablation Summary
    fig2, ax2 = plt.subplots(figsize=(6.8, 3.8))
    x2 = np.arange(len(configs))
    w2 = 0.25
    pooled_vals = [metrics["pooled_asr"][cfg]["pct"] for cfg in configs]
    tsr_vals = [metrics["utility_by_config"][cfg]["tsr_pct"] for cfg in configs]
    fbr_vals = [metrics["utility_by_config"][cfg]["fbr_pct"] for cfg in configs]

    ax2.bar(x2 - w2, pooled_vals, width=w2, label="Pooled ASR (%)", color="#c0392b")
    ax2.bar(x2, tsr_vals, width=w2, label="Benign TSR (%)", color="#27ae60")
    ax2.bar(x2 + w2, fbr_vals, width=w2, label="Benign FBR (%)", color="#7f8c8d")
    ax2.set_xticks(x2)
    ax2.set_xticklabels([_CONFIG_DISPLAY.get(c, c).split()[0] for c in configs])
    ax2.set_ylabel("Percentage (%)")
    ax2.set_ylim(0, 112)
    ax2.set_title("Security vs. Benign Utility Across Configurations", pad=28)
    ax2.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3, frameon=True, fontsize=8.5)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    fig2.tight_layout()
    for ext in ("pdf", "png"):
        p = dest / f"fig_utility_vs_security.{ext}"
        fig2.savefig(p, dpi=200)
        written.append(str(p))
    plt.close(fig2)

    # 3. Figure 3: Causal Gate Pass Probability Curves (Theorem 2)
    fig3, ax3 = plt.subplots(figsize=(6.5, 3.8))
    q_grid = np.linspace(0.0, 1.0, 101)
    for k_val, style in ((1, "--"), (3, "-."), (5, "-"), (9, ":")):
        probs = [binomial_pass_probability(k_val, float(q), 0.5) for q in q_grid]
        ax3.plot(q_grid, probs, linestyle=style, linewidth=2.0, label=f"k = {k_val}")

    ax3.axvline(0.5, color="#7f8c8d", linestyle=":", linewidth=1.2, label="theta = 0.5")
    ax3.set_xlabel("Single-trial Trusted Support Probability (q)")
    ax3.set_ylabel("Gate Pass Probability")
    ax3.set_title("Causal Gate Discrimination Curve (Theorem 2)")
    ax3.legend(loc="lower right", frameon=True)
    ax3.grid(True, linestyle="--", alpha=0.4)
    fig3.tight_layout()
    for ext in ("pdf", "png"):
        p = dest / f"fig_gate_calibration.{ext}"
        fig3.savefig(p, dpi=200)
        written.append(str(p))
    plt.close(fig3)

    return written
