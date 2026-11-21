"""Plots generated only from result files, with mandatory integrity labels."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def plot_results(input_path: str | Path, output_dir: str | Path) -> list[Path]:
    source = Path(input_path)
    data = json.loads(source.read_text(encoding="utf-8"))
    kind = str(data.get("result_kind", "unknown provenance"))
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    rates = data.get("attack_success_rate_by_channel", {})
    if not rates:
        raise ValueError("Input has no attack_success_rate_by_channel mapping")
    labels = list(rates)
    values = [rates[label] for label in labels]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(range(len(labels)), values, color="#335c81")
    ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Attack success rate")
    ax.set_title(f"ProvGuard channel outcomes\n{kind}")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = destination / "attack_success_by_channel.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return [path]

