"""Chart generation for PPT reports using matplotlib.

Matches the SEO_Monthly_Report_Sample_Template style:
- Clean white background, minimal grid
- PRIMARY_BLUE (#2563EB) line/bar color
- Small font sizes for labels
- 96 DPI for sharp embedding in 13.333"x7.5" slides
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# Force non-interactive Agg backend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.font_manager as fm

# ── Chart color palette (matches ppt_design.py) ──
NAVY = "#0F2747"
PRIMARY_BLUE = "#2563EB"
GREEN = "#16A34A"
AMBER = "#F59E0B"
RED = "#DC2626"
TEAL = "#14B8A6"
GRAY_MID = "#475569"
GRAY_LINE = "#E2E8F0"
WHITE = "#FFFFFF"

DPI = 120
FONT_FAMILY = "Calibri"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Calibri", "DejaVu Sans", "Arial"],
    "axes.edgecolor": GRAY_LINE,
    "axes.linewidth": 0.6,
    "grid.color": GRAY_LINE,
    "grid.alpha": 0.5,
    "xtick.color": GRAY_MID,
    "ytick.color": GRAY_MID,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
})


def _save_fig(fig) -> bytes:
    """Render a matplotlib figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight",
                pad_inches=0.1, facecolor=WHITE, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════
# 1. Traffic line chart (Slide 3 — Website Traffic Overview)
# ═══════════════════════════════════════════════════════════════

def make_traffic_line_chart(
    monthly_data: list[dict],
    width: float = 6.4,
    height: float = 4.6,
) -> bytes:
    """Line chart showing organic traffic trend over months.
    
    monthly_data: list of {month, users} dicts, ordered chronologically.
    """
    months = [d.get("month", f"M{i+1}") for i, d in enumerate(monthly_data)]
    values = []
    for d in monthly_data:
        try:
            values.append(int(str(d.get("users", 0)).replace(",", "")))
        except (ValueError, TypeError):
            values.append(0)
    
    if not values or all(v == 0 for v in values):
        return b""
    
    fig, ax = plt.subplots(1, 1, figsize=(width, height), dpi=DPI)
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    
    x = range(len(months))
    ax.plot(x, values, color=PRIMARY_BLUE, linewidth=2.5, marker="o",
            markersize=6, markerfacecolor=WHITE, markeredgecolor=PRIMARY_BLUE,
            markeredgewidth=1.5, zorder=3)
    
    # Fill under the line
    ax.fill_between(x, values, alpha=0.08, color=PRIMARY_BLUE, zorder=1)
    
    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=0)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linewidth=0.4, alpha=0.4)
    ax.grid(axis="x", visible=False)
    
    ax.set_xlim(-0.3, len(months) - 0.7)
    
    return _save_fig(fig)


# ═══════════════════════════════════════════════════════════════
# 2. PSI column chart (Slide 7 — Core Web Vitals)
# ═══════════════════════════════════════════════════════════════

def make_psi_column_chart(
    desktop_score: int | float,
    mobile_score: int | float,
    width: float = 4.6,
    height: float = 3.0,
) -> bytes:
    """Clustered column chart comparing Desktop vs Mobile PSI scores."""
    fig, ax = plt.subplots(1, 1, figsize=(width, height), dpi=DPI)
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    
    labels = ["Desktop", "Mobile"]
    values = [desktop_score, mobile_score]
    colors = [GREEN, AMBER]
    
    bars = ax.bar(labels, values, width=0.5, color=colors, edgecolor="none",
                  zorder=3)
    
    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                f"{int(val)}", ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=NAVY)
    
    ax.set_ylim(0, 105)
    ax.set_ylabel("Score", fontsize=8, color=GRAY_MID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linewidth=0.4, alpha=0.4)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelsize=9)
    
    # 100 reference line
    ax.axhline(y=100, color=GRAY_LINE, linewidth=0.5, linestyle="--", zorder=1)
    
    return _save_fig(fig)


# ═══════════════════════════════════════════════════════════════
# 3. Keyword Distribution horizontal bar (Slide 9 — Competitors)
# ═══════════════════════════════════════════════════════════════

def make_distribution_hbar_chart(
    distribution: dict,
    width: float = 5.0,
    height: float = 3.0,
) -> bytes:
    """Horizontal bar chart of keyword position distribution.
    
    distribution: dict like {"#1": 1, "Top 3": 2, "Top 10": 3, ...}
    """
    # Maps from ppt_data.py keys to display labels
    mapping = [
        ("p1", "#1", GREEN),
        ("top3", "Top 3", PRIMARY_BLUE),
        ("top10", "Top 10", AMBER),
        ("p11_20", "11-20", RED),
        ("beyond", "Beyond", GRAY_MID),
    ]
    labels = []
    values = []
    bar_colors = []
    for key, label, color in mapping:
        v = distribution.get(key, 0)
        try:
            v = int(v)
        except (ValueError, TypeError):
            v = 0
        labels.append(label)
        values.append(v)
        bar_colors.append(color)
    
    fig, ax = plt.subplots(1, 1, figsize=(width, height), dpi=DPI)
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    
    y_pos = range(len(labels))
    bars = ax.barh(y_pos, values, height=0.55, color=bar_colors,
                   edgecolor="none", zorder=3)
    
    # Value labels
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    str(val), ha="left", va="center",
                    fontsize=10, fontweight="bold", color=NAVY)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", linewidth=0.4, alpha=0.4)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, max(values) * 1.4 + 0.5 if max(values) > 0 else 5)
    
    return _save_fig(fig)


# ═══════════════════════════════════════════════════════════════
# 4. Rank trend chart (individual keyword, used by generator.py)
# ═══════════════════════════════════════════════════════════════

def rank_trend_chart(
    keyword: str,
    history_records: list[dict],
    width: float = 3.0,
    height: float = 1.5,
) -> bytes:
    """Small line chart showing a single keyword's rank trend over time."""
    from collections import defaultdict
    group: dict[str, list[int]] = defaultdict(list)
    for row in history_records:
        kw = str(row.get("Keyword", "") or "").strip().lower()
        if kw == keyword.strip().lower():
            try:
                pos = int(str(row.get("Position", "0")).strip())
                if pos <= 0:
                    continue
            except (ValueError, TypeError):
                continue
            date = str(row.get("Date") or row.get("Month") or "").strip()
            if date:
                group[date].append(pos)

    dates = sorted(group.keys())
    if not dates:
        return b""
    avg_positions = [sum(group[d]) / len(group[d]) for d in dates]

    fig, ax = plt.subplots(1, 1, figsize=(width, height), dpi=100)
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    x = range(len(dates))
    ax.plot(x, avg_positions, color=PRIMARY_BLUE, linewidth=2, marker="o",
            markersize=5, markerfacecolor=WHITE, markeredgecolor=PRIMARY_BLUE,
            markeredgewidth=1.2, zorder=3)
    ax.fill_between(x, avg_positions, alpha=0.08, color=PRIMARY_BLUE, zorder=1)

    ax.set_xticks(x)
    ax.set_xticklabels([d[-5:] for d in dates], fontsize=7, rotation=0)
    ax.invert_yaxis()
    ax.set_ylim(max(0, min(avg_positions) - 2), max(avg_positions) + 2)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linewidth=0.3, alpha=0.3)
    ax.grid(axis="x", visible=False)
    ax.tick_params(labelsize=7)

    return _save_fig(fig)
