"""Presentation-quality visualizations for the saliency-guided compression
pipeline. Each `plot_*` function produces one self-contained figure and saves
it to disk at high DPI."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch

# ---------- Global presentation styling ----------

mpl.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#1a1a1a",
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "savefig.dpi": 180,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

SALIENCY_CMAP = LinearSegmentedColormap.from_list(
    "saliency", [(0.05, 0.0, 0.20), (0.45, 0.0, 0.55), (0.95, 0.45, 0.10), (1.0, 1.0, 0.55)]
)
ZONES_CMAP = LinearSegmentedColormap.from_list(
    "zones", ["#1f4e79", "#3a7ca5", "#81b1d3", "#f4a261", "#e76f51"]
)


def _show_image(ax, img, title=None):
    ax.imshow(img.astype(np.uint8) if img.dtype != np.uint8 else img)
    ax.set_xticks([]); ax.set_yticks([])
    if title:
        ax.set_title(title)


def _show_saliency(ax, sal, title=None):
    im = ax.imshow(sal, cmap=SALIENCY_CMAP, vmin=0, vmax=1)
    ax.set_xticks([]); ax.set_yticks([])
    if title:
        ax.set_title(title)
    return im


def _fmt_kb(num_bytes: int) -> str:
    return f"{num_bytes / 1024:.1f} KB"


# ---------- Step 1: saliency analysis ----------

def plot_saliency_analysis(
    original: np.ndarray, saliency: np.ndarray, source_label: str, out_path: str
) -> None:
    """Original | Saliency map | Overlay | Histogram of saliency values."""
    fig, axes = plt.subplots(1, 4, figsize=(20, 5), constrained_layout=True)

    _show_image(axes[0], original, "Step 1a — Original input")

    im = _show_saliency(axes[1], saliency, f"Step 1b — Saliency map")
    cbar = fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)
    cbar.set_label("saliency", fontsize=9)

    _show_image(axes[2], original, "Step 1c — Saliency overlay")
    axes[2].imshow(saliency, cmap=SALIENCY_CMAP, alpha=0.55, vmin=0, vmax=1)

    axes[3].hist(saliency.ravel(), bins=40, color="#3a7ca5", edgecolor="#1f4e79")
    axes[3].set_title("Step 1d — Saliency distribution")
    axes[3].set_xlabel("normalized saliency"); axes[3].set_ylabel("pixel count")
    axes[3].spines["top"].set_visible(False); axes[3].spines["right"].set_visible(False)

    fig.suptitle(f"Step 1 — Saliency analysis  ·  source: {source_label}",
                 fontsize=16, fontweight="bold")
    fig.savefig(out_path); plt.close(fig)


# ---------- Step 2: blur pyramid ----------

def plot_blur_pyramid(pyramid: List[np.ndarray], sigma_step: float, out_path: str) -> None:
    n = len(pyramid)
    fig, axes = plt.subplots(1, n, figsize=(3.4 * n, 4))
    if n == 1:
        axes = [axes]
    for i, (ax, layer) in enumerate(zip(axes, pyramid)):
        sigma = 0 if i == 0 else sigma_step * i
        title = "Sharp (σ=0)" if i == 0 else f"Level {i}  σ={sigma:.1f}"
        _show_image(ax, layer, title)
    fig.suptitle("Step 2 — Multi-resolution low-pass pyramid",
                 fontsize=16, fontweight="bold", y=1.02)
    fig.text(0.5, -0.04,
             "Each level removes more high-frequency detail. The encoder "
             "spends almost no bits on smooth regions.",
             ha="center", fontsize=10, style="italic", color="#444")
    fig.tight_layout()
    fig.savefig(out_path); plt.close(fig)


# ---------- Step 3: level-selection field ----------

def plot_level_field(
    original: np.ndarray, saliency: np.ndarray, level_field: np.ndarray,
    num_levels: int, out_path: str
) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(22, 5), constrained_layout=True)

    _show_image(axes[0], original, "Original")
    _show_saliency(axes[1], saliency, "Saliency (input)")

    im = axes[2].imshow(level_field, cmap=ZONES_CMAP, vmin=0, vmax=num_levels - 1)
    axes[2].set_xticks([]); axes[2].set_yticks([])
    axes[2].set_title("Pyramid index (continuous)")
    cbar = fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)
    cbar.set_label("level", fontsize=9)

    quantized = np.round(level_field).astype(int)
    im2 = axes[3].imshow(quantized, cmap=ZONES_CMAP, vmin=0, vmax=num_levels - 1)
    axes[3].set_xticks([]); axes[3].set_yticks([])
    axes[3].set_title("Quality zones (discrete)")
    cbar2 = fig.colorbar(im2, ax=axes[3], fraction=0.046, pad=0.04,
                         ticks=list(range(num_levels)))
    cbar2.set_label("zone", fontsize=9)

    fig.suptitle("Step 3 — Map saliency to a per-pixel quality level",
                 fontsize=16, fontweight="bold")
    fig.savefig(out_path); plt.close(fig)


# ---------- Step 4: composite assembly ----------

def plot_composite_assembly(
    original: np.ndarray, composite: np.ndarray, level_field: np.ndarray, out_path: str
) -> None:
    """Original | composite | abs-difference heatmap to show what was thrown away."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    _show_image(axes[0], original, "Original (full detail)")
    _show_image(axes[1], composite, "Step 4 — Saliency-aware composite")

    diff = np.abs(original.astype(np.int32) - composite.astype(np.int32)).mean(axis=-1)
    im = axes[2].imshow(diff, cmap="magma", vmin=0, vmax=max(diff.max(), 1))
    axes[2].set_xticks([]); axes[2].set_yticks([])
    axes[2].set_title("Detail removed (per-pixel |Δ|)")
    fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.02).set_label(
        "luminance change", fontsize=9)

    fig.suptitle("Step 4 — Blend pyramid layers per pixel using the level field",
                 fontsize=16, fontweight="bold", y=1.02)
    fig.text(0.5, -0.02,
             "The composite preserves all detail in salient regions and "
             "smooths the rest, dramatically reducing high-frequency "
             "DCT energy before encoding.",
             ha="center", fontsize=10, style="italic", color="#444")
    fig.tight_layout()
    fig.savefig(out_path); plt.close(fig)


# ---------- Step 5: encoded comparison ----------

def plot_encoding_comparison(comparisons: List[Dict], out_path: str) -> None:
    """One row per encoding: thumbnail, file size, PSNR, saliency-PSNR."""
    n = len(comparisons)
    fig = plt.figure(figsize=(5 * n, 6))
    gs = GridSpec(2, n, figure=fig, height_ratios=[5, 1.2], hspace=0.05, wspace=0.06)

    for i, c in enumerate(comparisons):
        ax = fig.add_subplot(gs[0, i])
        _show_image(ax, c["image"], c["title"])
        # subtle border accent
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(c.get("accent", "#cccccc"))
            spine.set_linewidth(2.5)

        info_ax = fig.add_subplot(gs[1, i]); info_ax.axis("off")
        lines = [
            f"file size:    {_fmt_kb(c['bytes'])}",
            f"PSNR:         {c['psnr']:.2f} dB",
            f"focal-PSNR:   {c.get('focal_psnr', float('nan')):.2f} dB  (top-20% salient)",
            f"saliency-PSNR: {c['s_psnr']:.2f} dB  (full weighted)",
        ]
        if "quality" in c:
            lines.insert(0, f"JPEG quality: {c['quality']}")
        info_ax.text(0.02, 0.95, "\n".join(lines),
                     family="monospace", fontsize=11, va="top",
                     bbox=dict(boxstyle="round,pad=0.5",
                               facecolor="#f7f7f7", edgecolor="#cccccc"))

    fig.suptitle("Step 5 — Side-by-side encoding comparison",
                 fontsize=16, fontweight="bold", y=0.98)
    fig.savefig(out_path); plt.close(fig)


# ---------- Bonus: rate-distortion curves ----------

def plot_rate_distortion(rd_data: Dict[str, List[Dict]], out_path: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for label, rows in rd_data.items():
        sizes_kb = [r["bytes"] / 1024 for r in rows]
        psnrs = [r["psnr"] for r in rows]
        focal_psnrs = [r.get("focal_psnr", r["s_psnr"]) for r in rows]
        axes[0].plot(sizes_kb, psnrs, marker="o", label=label, linewidth=2)
        axes[1].plot(sizes_kb, focal_psnrs, marker="o", label=label, linewidth=2)

    for ax, ylabel, title in [
        (axes[0], "PSNR (dB)", "Uniform PSNR vs file size"),
        (axes[1], "Focal PSNR (dB, top-20% salient)",
         "Quality where the eye actually looks"),
    ]:
        ax.set_xlabel("file size (KB)"); ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3); ax.legend()
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    fig.suptitle("Step 6 — Rate-distortion: more quality per byte where attention goes",
                 fontsize=16, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(out_path); plt.close(fig)


# ---------- Final overview poster ----------

def plot_pipeline_overview(
    original: np.ndarray, saliency: np.ndarray, level_field: np.ndarray,
    composite: np.ndarray, encoded: np.ndarray, encoded_size: int, out_path: str
) -> None:
    fig = plt.figure(figsize=(22, 6))
    gs = GridSpec(1, 5, figure=fig, wspace=0.18)
    titles = [
        "1. Input image",
        "2. Saliency map",
        "3. Quality field",
        "4. Composite",
        f"5. Encoded JPEG  ({_fmt_kb(encoded_size)})",
    ]
    panels = [original, saliency, level_field, composite, encoded]
    cmaps = [None, SALIENCY_CMAP, ZONES_CMAP, None, None]

    for i, (panel, title, cmap) in enumerate(zip(panels, titles, cmaps)):
        ax = fig.add_subplot(gs[i])
        if cmap is None:
            ax.imshow(panel.astype(np.uint8) if panel.dtype != np.uint8 else panel)
        else:
            ax.imshow(panel, cmap=cmap)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(title, fontsize=13, fontweight="bold")

    # (arrows between panels removed -- gridspec already implies sequence)

    fig.suptitle("Saliency-Guided Image Compression — End-to-End Pipeline",
                 fontsize=18, fontweight="bold", y=1.04)
    fig.savefig(out_path); plt.close(fig)
