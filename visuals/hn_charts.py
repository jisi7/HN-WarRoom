#!/usr/bin/env python3
"""HN scientific-chart renderer (siimland/bodybio aesthetic).

Renders a chart *spec* -> 1080x1080 PNG bytes, ready to upload to Cloudinary and
attach to a social post (Facebook / Threads / X) or an article header.

Design signed off with Jorge (prototype v7):
  - descriptive TITLE = the takeaway (not an axis label); rotated across styles
  - red STAT line (the quantified punch)
  - broken y-axis so real differences read big
  - error bars + significance bracket + plain-English significance footnote
  - product-coloured highlight, source citation, HN wordmark

Data must be REAL (from a cited study) — never AI-guessed. Callers pass `source`.
"""
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# HN palette (from the brand brief)
COLORS = {
    "creatine":  "#D2042D",   # cherry red
    "focase":    "#24418F",   # dark blue
    "vitamin_d": "#C8893A",   # orange
    "general":   "#A39888",   # brown
}
CHARCOAL = "#2C2A27"; MUTED = "#C9C4BC"; SOFT = "#8a857f"; BROWN = "#A39888"; FAINT = "#A39D95"

# The 5 title styles Jorge chose to rotate (+ occasional others to test).
TITLE_STYLES = ["mechanism", "myth_buster", "benefit", "stat_forward", "significance"]
TITLE_STYLES_TEST = ["curiosity", "verdict", "head_to_head"]

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": CHARCOAL})


def _footer(fig, source, sig_text):
    if sig_text:
        fig.text(0.5, 0.115,
                 "*  statistically significant (p < 0.05) — the difference is very unlikely to be chance",
                 ha="center", fontsize=12, color=FAINT)
    fig.text(0.5, 0.072, source, ha="center", fontsize=13.5, color=SOFT, style="italic")
    fig.text(0.5, 0.030, "HOLISTIC  NUTRITION", ha="center", fontsize=15, fontweight="bold", color=BROWN)


def _header(fig, title, stat, hi):
    fig.text(0.5, 0.885, title, ha="center", va="center", fontsize=23, color=CHARCOAL, wrap=True)
    if stat:
        fig.text(0.5, 0.825, stat, ha="center", va="center", fontsize=26, fontweight="bold", color=hi)
        fig.add_artist(plt.Line2D([0.44, 0.56], [0.785, 0.785], color=hi, lw=3))


def _yaxis_break(ax):
    for off in (0.020, 0.045):
        ax.plot([-0.011, 0.011], [off - 0.011, off + 0.011], transform=ax.transAxes,
                color=CHARCOAL, lw=1.7, clip_on=False, solid_capstyle="round")


def _finish(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def render_bar_chart(title, stat, ylabel, labels, values, errors,
                     product="general", highlight_idx=None, source="", sig_text="*  p < 0.05",
                     broken_axis=True, out=None):
    hi = COLORS.get(product, COLORS["general"])
    if highlight_idx is None:
        highlight_idx = max(range(len(values)), key=lambda i: values[i])
    fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0.17, 0.205, 0.72, 0.51]); ax.set_facecolor("white")

    x = list(range(len(values)))
    cols = [hi if i == highlight_idx else MUTED for i in x]
    ax.bar(x, values, width=0.52, color=cols, zorder=3, yerr=errors, capsize=10,
           error_kw={"elinewidth": 2.2, "ecolor": CHARCOAL, "capthick": 2.2, "zorder": 4})
    for i, v in enumerate(values):
        ax.text(i, v + errors[i] + (max(values) * 0.004), f"{v:g}", ha="center", va="bottom",
                fontsize=21, fontweight="bold", color=(hi if i == highlight_idx else SOFT))

    lo = min(values[i] - errors[i] for i in x)
    top = max(values[i] + errors[i] for i in x)
    base = (lo - (top - lo) * 0.55) if broken_axis else 0
    span = top - base
    y_br = top + span * 0.22; leg = span * 0.045
    ax.plot([0, 0, len(x)-1, len(x)-1], [y_br-leg, y_br, y_br, y_br-leg], lw=2,
            color=CHARCOAL, zorder=5, solid_capstyle="round")
    if sig_text:
        ax.text((len(x)-1)/2, y_br + span*0.02, sig_text, ha="center", va="bottom",
                fontsize=20, fontweight="bold", color=CHARCOAL)
    ax.set_ylim(base, y_br + span * 0.14)
    if broken_axis:
        _yaxis_break(ax)

    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=21, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=17, labelpad=12)
    ax.tick_params(axis="y", labelsize=14, colors=SOFT, length=0)
    ax.tick_params(axis="x", length=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#DDD8D0")
    ax.spines["bottom"].set_color(CHARCOAL); ax.spines["bottom"].set_linewidth(1.6)

    _header(fig, title, stat, hi); _footer(fig, source, sig_text)
    data = _finish(fig)
    if out:
        open(out, "wb").write(data)
    return data


def render_line_chart(title, stat, ylabel, xlabels, values, errors,
                      product="general", star_idx=None, source="", sig_text="*  p < 0.05", out=None):
    """Time-course line chart (siimland style): points + error bars, optional * on one point."""
    hi = COLORS.get(product, COLORS["general"])
    fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0.17, 0.205, 0.72, 0.51]); ax.set_facecolor("white")

    x = list(range(len(values)))
    ax.plot(x, values, "-", color=CHARCOAL, lw=2.4, zorder=3)
    ax.errorbar(x, values, yerr=errors, fmt="o", ms=11, color=hi, ecolor=CHARCOAL,
                elinewidth=2, capsize=8, capthick=2, zorder=4)
    if star_idx is not None:
        ax.text(star_idx, values[star_idx] + errors[star_idx] + (max(values)*0.02), "*",
                ha="center", va="bottom", fontsize=30, fontweight="bold", color=CHARCOAL)

    lo = min(values[i] - errors[i] for i in x); top = max(values[i] + errors[i] for i in x)
    base = lo - (top - lo) * 0.55; span = top - base
    ax.set_ylim(base, top + span * 0.18)
    _yaxis_break(ax)
    ax.set_xticks(x); ax.set_xticklabels(xlabels, fontsize=17, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=17, labelpad=12)
    ax.tick_params(axis="y", labelsize=14, colors=SOFT, length=0)
    ax.tick_params(axis="x", length=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#DDD8D0")
    ax.spines["bottom"].set_color(CHARCOAL); ax.spines["bottom"].set_linewidth(1.6)

    _header(fig, title, stat, hi); _footer(fig, source, sig_text)
    data = _finish(fig)
    if out:
        open(out, "wb").write(data)
    return data


if __name__ == "__main__":
    D = r"C:\Users\jorge\Downloads\Claude Dropbox"
    # myth-buster style
    render_bar_chart("Creatine's water goes inside the cell — not bloat", "+9.5% water inside the cell",
                     "Intracellular water (L)", ["Placebo", "Creatine"], [26.4, 28.9], [0.8, 0.9],
                     product="creatine", source="Powers et al., J Athl Train — representative values",
                     out=D + r"\HN_chart_mythbuster.png")
    # stat-forward style, focase (blue)
    render_bar_chart("Alpha-GPC sharpened reaction time", "18% faster on task",
                     "Reaction time improvement (%)", ["Placebo", "Alpha-GPC"], [6.0, 18.0], [2.0, 2.4],
                     product="focase", source="Represents a cited nootropic RCT — placeholder values",
                     out=D + r"\HN_chart_statforward.png")
    # line / time-course
    render_line_chart("Muscle creatine climbs over a loading week", "+20% by day 5",
                      "Muscle phosphocreatine (mmol/kg)", ["Pre", "D1", "D2", "D3", "D4", "D5"],
                      [100, 106, 112, 116, 119, 120], [3, 3, 3, 3, 3, 3], product="creatine", star_idx=5,
                      source="Represents a cited loading study — placeholder values",
                      out=D + r"\HN_chart_line.png")
    print("rendered 3 samples")
