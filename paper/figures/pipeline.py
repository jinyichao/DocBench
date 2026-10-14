"""Generates figures/pipeline.pdf: the end-to-end system workflow for the paper.

Run from paper/:  python3 figures/pipeline.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
})

INK      = "#1a1a1a"
LINE     = "#5a5a5a"
BOX_EDGE = "#8a8a8a"
BOX_FILL = "#f2f2f0"
ACC_EDGE = "#1f4e79"
ACC_FILL = "#dbe7f3"
SEC_EDGE = "#7a5c2e"
SEC_FILL = "#f4e9d5"

W, H = 100.0, 44.0
fig, ax = plt.subplots(figsize=(6.3, 6.3 * H / W))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
ax.set_position([0, 0, 1, 1])

TITLE_SZ, BODY_SZ, EDGE_SZ = 7.6, 6.1, 5.9
LINE_H, PAD_TOP, PAD_BOT = 2.9, 3.0, 2.2


class Box:
    def __init__(self, cx, cy, w, title, lines, fill, edge, lw):
        h = PAD_TOP + 3.4 + LINE_H * len(lines) + PAD_BOT
        self.x0, self.x1 = cx - w / 2, cx + w / 2
        self.y0, self.y1 = cy - h / 2, cy + h / 2
        self.cx, self.cy = cx, cy
        ax.add_patch(FancyBboxPatch(
            (self.x0, self.y0), w, h,
            boxstyle="round,pad=0,rounding_size=1.3",
            facecolor=fill, edgecolor=edge, linewidth=lw, zorder=2))
        y = self.y1 - PAD_TOP
        ax.text(cx, y, title, ha="center", va="top",
                fontsize=TITLE_SZ, fontweight="bold", color=INK, zorder=3)
        y -= 3.6
        for ln in lines:
            ax.text(cx, y, ln, ha="center", va="top",
                    fontsize=BODY_SZ, color=LINE, zorder=3)
            y -= LINE_H

    def left(self, dy=0.0):
        return (self.x0, self.cy + dy)

    def right(self, dy=0.0):
        return (self.x1, self.cy + dy)


def node(cx, cy, w, title, lines, fill=BOX_FILL, edge=BOX_EDGE, lw=0.8):
    return Box(cx, cy, w, title, lines, fill, edge, lw)


def arrow(p, q, rad=0.0, ls="-", color=LINE, lw=0.85):
    ax.add_patch(FancyArrowPatch(
        p, q, arrowstyle="-|>", mutation_scale=7.5, linewidth=lw,
        color=color, linestyle=ls,
        connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0, zorder=1))


MID = 22.0

A = node(8.0, MID, 15.0, "Page image",
         ["single scan,", "median 968 px"])
B = node(29.5, MID, 21.0, "Image upscaling",
         [r"long edge $\rightarrow$ 2000 px", "JPEG q100, no subsampling"],
         fill=ACC_FILL, edge=ACC_EDGE, lw=1.4)
C = node(52.0, MID, 16.0, "Layout router",
         ["DocLayout-YOLO", "flags table pages"])
D = node(74.5, 35.0, 19.0, "Gemini 3.7-Flash",
         ["table pages +", "blocked-page recovery"], fill=SEC_FILL, edge=SEC_EDGE)
E = node(74.5, 9.0, 19.0, "Qwen3.8-max",
         ["all pages,", "thinking disabled"], fill=ACC_FILL, edge=ACC_EDGE)
F = node(92.0, MID, 14.0, "Assembly",
         ["guarded table", "swap; manifest", "check"])

arrow(A.right(), B.left())
arrow(B.right(), C.left())
arrow((C.x1, MID + 3.0), D.left(-1.5), rad=0.18)
arrow((C.x1, MID - 3.0), E.left(1.5), rad=-0.18)
arrow(D.right(-1.5), (F.x0, MID + 3.0), rad=0.18)
arrow(E.right(1.5), (F.x0, MID - 3.0), rad=-0.18)

# output of the pipeline
ax.annotate("", xy=(F.cx, F.y0 - 5.2), xytext=(F.cx, F.y0),
            arrowprops=dict(arrowstyle="-|>", mutation_scale=7.5,
                            linewidth=0.85, color=LINE))
ax.text(F.cx, F.y0 - 6.0, "predictions.jsonl", ha="center", va="top",
        fontsize=BODY_SZ, color=INK, zorder=3)

# the two engines share one prompt
px0, px1, py = 65.0, 84.0, MID
ax.add_patch(FancyBboxPatch(
    (px0, py - 2.2), px1 - px0, 4.4,
    boxstyle="round,pad=0,rounding_size=1.1",
    facecolor="white", edgecolor=BOX_EDGE, linewidth=0.7,
    linestyle=(0, (2.4, 2.0)), zorder=2))
ax.text((px0 + px1) / 2, py, "one shared prompt (App. A)", ha="center",
        va="center", fontsize=EDGE_SZ, color=LINE, zorder=3)
for y_to in (D.y0, E.y1):
    ax.plot([(px0 + px1) / 2] * 2, [py + (2.2 if y_to > py else -2.2), y_to],
            color=BOX_EDGE, linewidth=0.7, linestyle=(0, (1.6, 1.6)), zorder=1)

fig.savefig("figures/pipeline.pdf", bbox_inches="tight", pad_inches=0.03)
fig.savefig("figures/pipeline.png", dpi=300, bbox_inches="tight", pad_inches=0.03)
