"""Chart assets for the PDF report."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from column_mapping import find_column


def _value_label(value: float, concept: str) -> str:
    if concept in {"funding", "valuation", "revenue", "burn_rate"}:
        if abs(value) >= 1_000_000: return f"${value / 1_000_000:.1f}M"
        if abs(value) >= 1_000: return f"${value / 1_000:.1f}K"
        return f"${value:,.0f}"
    if concept == "growth": return f"{value:.1f}%"
    return f"{value:,.0f}"


def create_charts(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Create metric charts for one company record, never a portfolio trend."""
    output_dir.mkdir(parents=True, exist_ok=True)
    charts = []
    concepts = [("revenue", "Revenue"), ("funding", "Funding"), ("employees", "Employee Count"), ("growth", "Growth Rate"), ("burn_rate", "Monthly Burn"), ("runway", "Cash Runway (months)"), ("valuation", "Valuation")]
    for concept, title in concepts:
        column = find_column(frame.columns, concept)
        if not column: continue
        values = pd.to_numeric(frame[column].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce").dropna()
        if values.empty: continue
        fig, ax = plt.subplots(figsize=(7.2, 2.35)); fig.patch.set_facecolor("#ffffff")
        value = values.iloc[0]
        color = "#155E75" if concept in {"funding", "valuation"} else "#0F766E"
        ax.barh([title], [value], color=color, height=.42, edgecolor="none")
        upper = max(abs(value) * 1.28, 1)
        ax.set_xlim(min(0, value * 0.08), upper if value >= 0 else abs(value) * 0.08)
        ax.text(value + (upper * .025 if value >= 0 else -upper * .025), 0, _value_label(value, concept), va="center", ha="left" if value >= 0 else "right", fontsize=10, color="#123047", fontweight="bold")
        ax.set_title(title, loc="left", fontweight="bold", color="#123047", pad=12)
        ax.set_xlabel("Reported value"); ax.grid(axis="x", alpha=.14, color="#94A3B8"); ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0); ax.tick_params(axis="x", labelsize=8, colors="#64748B"); ax.ticklabel_format(axis="x", style="plain", useOffset=False)
        path = output_dir / f"{concept}.png"; fig.tight_layout(); fig.savefig(path, dpi=180, bbox_inches="tight"); plt.close(fig); charts.append(path)
    return charts
