"""Regenerate Figure 1 of the paper (generated games, STABLE condition).

Median level-2 actions relative to Reset, 100 generated games per point,
6 decoys, k irrelevant object kinds (dense layout). Values from
results/compare_dense.txt.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator

K = [0, 16, 32, 48, 64]
SERIES = [
    ("Transfer", [1.45, 1.00, 0.76, 0.60, 0.55], "#d95f02", "o"),
    ("Selective", [0.22, 0.50, 0.60, 0.72, 0.68], "#1f78b4", "s"),
    ("Effective-thin", [0.12, 0.08, 0.06, 0.05, 0.05], "#1b9e77", "^"),
]

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Latin Modern Roman", "CMU Serif", "DejaVu Serif"],
    "mathtext.fontset": "cm",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

fig, ax = plt.subplots(figsize=(6.0, 3.4))
ax.axhline(1.0, color="0.45", lw=1, ls="--", zorder=1)
ax.text(64, 1.06, "Reset (start fresh)", ha="right", va="bottom", color="0.35", fontsize=9)
for name, ys, col, mk in SERIES:
    ax.plot(K, ys, color=col, marker=mk, ms=5, lw=1.8, zorder=3)
    ax.annotate(f"{name} {ys[-1]:.2f}$\\times$", (K[-1], ys[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", color=col, fontsize=9)
ax.set_yscale("log")
ticks = [0.05, 0.1, 0.25, 0.5, 1, 2]
ax.yaxis.set_major_locator(FixedLocator(ticks))
ax.yaxis.set_major_formatter(FixedFormatter([f"{t:g}$\\times$" for t in ticks]))
ax.yaxis.set_minor_locator(NullLocator())
ax.set_ylim(0.04, 2.1)
ax.set_xticks(K)
ax.set_xlim(-3, 82)
ax.spines["bottom"].set_bounds(0, 64)
ax.set_xlabel("Irrelevant object kinds on screen (each thinly tested)")
ax.set_ylabel("Level-2 actions relative to Reset")
ax.grid(axis="y", color="0.9", lw=0.8, zorder=0)
fig.tight_layout()
fig.savefig("figure1.pdf")
fig.savefig("figure1.png", dpi=300)
print("wrote figure1.pdf, figure1.png")
