"""Generates figures/submissions.pdf: leaderboard trajectory over our submissions.

All numbers are EvalAI Public Validation scores (509-page set) for the submissions
we actually made; Text is reported as 100(1-edit distance) to match the other
components. Run from paper/:  python3 figures/submissions.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
})

# label, Text, Table TEDS, Reading Order, Overall
SUBS = [
    ("Qwen\n+ table prompt", 77.33, 68.16, 67.99, 69.26),
    ("+ Gemini\ntables",    77.92, 69.00, 68.13, 69.65),
    ("+ upscale\n2000 px",  79.86, 69.87, 68.23, 70.68),
    ("+ smiles for\n2D structure", 79.89, 69.85, 68.27, 70.69),
    ("+ JPEG\nq100",        80.63, 69.35, 69.05, 71.33),
]
# submissions that were scored and then discarded (x is placed next to the
# accepted submission they were built on)
REJECTED = [("column-crop\nensemble", 2.55, 67.30), ("q90 table\nrevert", 5.45, 71.11)]

X = list(range(1, len(SUBS) + 1))
labels = [s[0] for s in SUBS]
text  = [s[1] for s in SUBS]
teds  = [s[2] for s in SUBS]
order = [s[3] for s in SUBS]
overall = [s[4] for s in SUBS]

ACC, GREY = "#1f4e79", "#8a8a8a"
C_TEXT, C_TEDS, C_ORDER = "#1f4e79", "#7a5c2e", "#4e7a58"

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.3, 2.45))
fig.subplots_adjust(left=0.065, right=0.995, bottom=0.30, top=0.90, wspace=0.22)


def style(ax, ylabel, title):
    ax.set_xlim(0.55, 5.95)
    ax.set_xticks(X)
    ax.set_xticklabels(labels, fontsize=6.0)
    ax.tick_params(axis="y", labelsize=6.6, length=2.5, pad=1.5)
    ax.tick_params(axis="x", length=2.5, pad=1.5)
    ax.set_ylabel(ylabel, fontsize=7.4, labelpad=2.5)
    ax.set_title(title, fontsize=7.8, pad=4.0)
    ax.grid(axis="y", color="#dddddd", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


# (a) Overall, with the two discarded submissions
ax1.plot(X, overall, "-o", color=ACC, linewidth=1.2, markersize=3.4, zorder=3)
for x, y in zip(X, overall):
    ax1.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 5),
                 ha="center", fontsize=6.0, color=ACC)
for name, x, y in REJECTED:
    ax1.plot([x], [y], marker="x", color=GREY, markersize=4.5,
             markeredgewidth=1.0, zorder=3)
    ax1.annotate(f"{name}\n{y:.2f}", (x, y), textcoords="offset points",
                 xytext=(0, -6), ha="center", va="top", fontsize=5.7, color=GREY)
ax1.set_ylim(65.6, 72.4)
style(ax1, "Overall", "(a) Overall per submission")

# (b) per-component
for ys, c, name, mk in ((text, C_TEXT, "Text", "o"),
                        (teds, C_TEDS, "Table TEDS", "s"),
                        (order, C_ORDER, "Reading Order", "^")):
    ax2.plot(X, ys, "-", marker=mk, color=c, linewidth=1.2, markersize=3.2,
             label=name, zorder=3)
ax2.set_ylim(66.8, 82.4)
style(ax2, "Component score", "(b) Scored components")
ax2.legend(fontsize=6.2, loc="upper left", frameon=False,
           handlelength=1.6, borderaxespad=0.2, labelspacing=0.25)

fig.savefig("figures/submissions.pdf", bbox_inches="tight", pad_inches=0.03)
fig.savefig("figures/submissions.png", dpi=300, bbox_inches="tight", pad_inches=0.03)
