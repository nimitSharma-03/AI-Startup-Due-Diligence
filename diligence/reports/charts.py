"""Matplotlib charts rendered to PNG bytes for the PDF report."""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

NAVY = "#0B1F3A"
TEAL = "#0F766E"
GREY = "#94A3B8"
INK = "#1E293B"
OUTCOME_COLORS = {"Operating": "#2563EB", "Exited": "#0F766E", "Dead": "#B91C1C"}


def _style(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#CBD5E1")
    ax.tick_params(colors="#475569", labelsize=8)
    ax.grid(axis="x", color="#E2E8F0", linewidth=0.6)
    ax.set_axisbelow(True)


def _png(fig) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buffer.getvalue()


def probability_chart(probabilities: dict[str, float], priors: dict[str, float]) -> bytes:
    labels = ["Operating", "Exited", "Dead"]
    fig, ax = plt.subplots(figsize=(6.4, 2.0))
    values = [probabilities[label] * 100 for label in labels]
    bars = ax.barh(labels, values, color=[OUTCOME_COLORS[label] for label in labels], height=0.5)
    for index, label in enumerate(labels):
        ax.plot([priors[label] * 100] * 2, [index - 0.32, index + 0.32], color=INK, linewidth=1.4)
    for bar, value in zip(bars, values):
        ax.text(bar.get_width() + 1.2, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", fontsize=8, color=INK)
    ax.set_xlim(0, 105)
    ax.invert_yaxis()
    ax.set_xlabel("Estimated probability (%)   |   black tick = historical base rate", fontsize=8, color="#475569")
    _style(ax)
    return _png(fig)


def funding_chart(reference_funding: list[float], amount: float | None) -> bytes:
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    values = np.log10(np.asarray([v for v in reference_funding if v > 0]))
    ax.hist(values, bins=24, color="#BFDBFE", edgecolor="white")
    if amount and amount > 0:
        ax.axvline(np.log10(amount), color=TEAL, linewidth=2)
        ax.text(np.log10(amount), ax.get_ylim()[1] * 0.92, "  this company", color=TEAL, fontsize=8, va="top")
    ticks = [3, 4, 5, 6, 7, 8, 9]
    ax.set_xticks(ticks, [r"\$1K", r"\$10K", r"\$100K", r"\$1M", r"\$10M", r"\$100M", r"\$1B"])
    ax.set_ylabel("Companies", fontsize=8, color="#475569")
    zero = sum(1 for v in reference_funding if v == 0)
    ax.set_xlabel(rf"Total funding, log scale (reference companies with funding > \$0; {zero} report \$0)", fontsize=8, color="#475569")
    _style(ax)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.6)
    return _png(fig)


def contribution_chart(explanation: list[dict], outcome: str) -> bytes:
    items = list(reversed(explanation))
    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(items) + 0.7))
    values = [item["contributions"][outcome] * 100 for item in items]
    labels = [f"{item['label']}: {item['value'][:38]}".replace("$", r"\$") for item in items]
    colors = [TEAL if value >= 0 else "#B91C1C" for value in values]
    ax.barh(labels, values, color=colors, height=0.55)
    ax.axvline(0, color="#64748B", linewidth=0.8)
    span = max(1.0, max(abs(v) for v in values) * 1.35)
    ax.set_xlim(-span, span)
    for index, value in enumerate(values):
        ax.text(value + (0.02 * span if value >= 0 else -0.02 * span), index, f"{value:+.1f} pts", va="center",
                ha="left" if value >= 0 else "right", fontsize=7.5, color=INK)
    ax.set_xlabel(f"Change in estimated P({outcome}) vs typical values (percentage points)", fontsize=8, color="#475569")
    _style(ax)
    return _png(fig)
