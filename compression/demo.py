"""End-to-end demo: load an image + saliency map, run the compression pipeline,
and emit (a) the compressed file and (b) presentation-quality figures for each
step. Runs in seconds on CPU.

Usage:
    python -m compression.demo
    python -m compression.demo --image path/to/img.jpg --gt-map path/to/map.png

The demo prefers the trained model checkpoint if one exists; otherwise it
falls back to the SALICON ground-truth map so the pipeline can be demonstrated
before training finishes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Make `models.*` importable when run as `python -m compression.demo`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compression import saliency_compress as sc
from compression import visualize as viz
from compression.saliency_inference import get_saliency_map


def _find_dataset_root() -> Path:
    """Walk upward from this file to find a `dataset/` directory."""
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        candidate = parent / "dataset" / "maps" / "val"
        if candidate.exists():
            return parent / "dataset"
        # also check sibling repo (when running inside a git worktree)
        candidate = parent.parent / "dataset" / "maps" / "val" if parent.parent != parent else None
    raise FileNotFoundError("Could not locate dataset/ directory.")


_DATASET = None
def _dataset_root() -> Path:
    global _DATASET
    if _DATASET is None:
        # Try walking up the worktree, then fall back to the canonical location.
        here = Path(__file__).resolve().parent
        for parent in [here, *here.parents]:
            candidate = parent / "dataset" / "maps" / "val"
            if candidate.exists():
                _DATASET = parent / "dataset"
                return _DATASET
        # Worktree fallback: dataset lives outside the worktree in the main repo.
        canonical = Path("C:/Users/Trevor/VidSalience/dataset")
        if (canonical / "maps" / "val").exists():
            _DATASET = canonical
            return _DATASET
        raise FileNotFoundError("Could not locate dataset/ directory.")
    return _DATASET


DEFAULT_IMAGE_NAME = "COCO_val2014_000000000133.jpg"
DEFAULT_MAP_NAME = "COCO_val2014_000000000133.png"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    ds = _dataset_root()
    p.add_argument("--image", default=str(ds / "images" / "images" / "val" / DEFAULT_IMAGE_NAME))
    p.add_argument("--gt-map", default=str(ds / "maps" / "val" / DEFAULT_MAP_NAME),
                   help="GT saliency map fallback (used if no checkpoint).")
    p.add_argument("--checkpoint", default="outputs/checkpoints/best.pth")
    p.add_argument("--out-dir", default="compression/outputs")
    p.add_argument("--baseline-quality", type=int, default=75,
                   help="JPEG quality for baseline + saliency-aware encode.")
    _defaults = sc.CompressionConfig()
    p.add_argument("--num-levels", type=int, default=_defaults.num_levels)
    p.add_argument("--sigma-step", type=float, default=_defaults.sigma_step)
    p.add_argument("--saliency-gamma", type=float, default=_defaults.saliency_gamma)
    return p.parse_args()


def main():
    args = parse_args()

    here = Path(__file__).resolve().parent
    def _resolve(p):
        return str((here.parent / p).resolve()) if not Path(p).is_absolute() else p
    image_path = _resolve(args.image)
    gt_map_path = _resolve(args.gt_map) if args.gt_map else None
    checkpoint_path = _resolve(args.checkpoint)
    out_dir = Path(_resolve(args.out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[1/6] Loading image: {image_path}")
    image = Image.open(image_path).convert("RGB")
    print(f"      Resolution: {image.size[0]}x{image.size[1]}")

    print(f"\n[2/6] Generating saliency map")
    saliency, source = get_saliency_map(image, checkpoint_path=checkpoint_path,
                                         gt_map_path=gt_map_path)
    print(f"      Source: {source}  (range [{saliency.min():.3f}, "
          f"{saliency.max():.3f}])")

    cfg = sc.CompressionConfig(
        num_levels=args.num_levels,
        sigma_step=args.sigma_step,
        saliency_gamma=args.saliency_gamma,
        jpeg_quality=args.baseline_quality,
    )

    print(f"\n[3/6] Building blur pyramid + composite")
    composite, intermediates = sc.saliency_compress(image, saliency, cfg)
    pyramid = intermediates["pyramid"]
    level_field = intermediates["level_field"]
    print(f"      Pyramid levels: {len(pyramid)}  "
          f"(max sigma = {(len(pyramid)-1) * cfg.sigma_step:.1f})")

    print(f"\n[4/6] Encoding outputs")
    original_arr = np.asarray(image)

    # Save the trio of encodings.
    base_path = out_dir / "baseline_uniform.jpg"
    sal_path = out_dir / "saliency_aware.jpg"
    base_size = sc.encode_image(original_arr, base_path,
                                 fmt="JPEG", quality=cfg.jpeg_quality)
    sal_size = sc.encode_image(composite, sal_path,
                                fmt="JPEG", quality=cfg.jpeg_quality)
    print(f"      Baseline JPEG (Q={cfg.jpeg_quality}):     "
          f"{base_size/1024:.1f} KB  -> {base_path.name}")
    print(f"      Saliency-aware JPEG (Q={cfg.jpeg_quality}): "
          f"{sal_size/1024:.1f} KB  -> {sal_path.name}  "
          f"(savings: {100 * (1 - sal_size / base_size):.1f}%)")

    # Equal-bitrate baseline: re-encode the original at lower Q to match
    # the saliency-aware file size, so we can compare visual quality fairly.
    eq_bytes, eq_q = sc.encode_to_target_size(original_arr, target_bytes=sal_size)
    eq_path = out_dir / "baseline_matched_size.jpg"
    eq_path.write_bytes(eq_bytes)
    print(f"      Matched-size baseline (Q={eq_q}): "
          f"{len(eq_bytes)/1024:.1f} KB  -> {eq_path.name}")

    # Decode-back arrays for metric comparison + visualization.
    base_decoded = np.asarray(Image.open(base_path).convert("RGB"))
    sal_decoded = np.asarray(Image.open(sal_path).convert("RGB"))
    eq_decoded = np.asarray(Image.open(eq_path).convert("RGB"))

    print(f"\n[5/6] Computing quality metrics")
    metrics_baseline = {
        "title": f"Baseline JPEG (Q={cfg.jpeg_quality})",
        "image": base_decoded, "bytes": base_size,
        "psnr": sc.psnr(original_arr, base_decoded),
        "s_psnr": sc.saliency_weighted_psnr(original_arr, base_decoded, saliency),
        "focal_psnr": sc.focal_psnr(original_arr, base_decoded, saliency),
        "quality": cfg.jpeg_quality, "accent": "#888",
    }
    metrics_eq = {
        "title": f"Baseline at matched size (Q={eq_q})",
        "image": eq_decoded, "bytes": len(eq_bytes),
        "psnr": sc.psnr(original_arr, eq_decoded),
        "s_psnr": sc.saliency_weighted_psnr(original_arr, eq_decoded, saliency),
        "focal_psnr": sc.focal_psnr(original_arr, eq_decoded, saliency),
        "quality": eq_q, "accent": "#3a7ca5",
    }
    metrics_sal = {
        "title": f"Saliency-aware JPEG (Q={cfg.jpeg_quality})",
        "image": sal_decoded, "bytes": sal_size,
        "psnr": sc.psnr(original_arr, sal_decoded),
        "s_psnr": sc.saliency_weighted_psnr(original_arr, sal_decoded, saliency),
        "focal_psnr": sc.focal_psnr(original_arr, sal_decoded, saliency),
        "quality": cfg.jpeg_quality, "accent": "#e76f51",
    }
    for m in (metrics_baseline, metrics_eq, metrics_sal):
        print(f"      {m['title']:<40s}  "
              f"{m['bytes']/1024:6.1f} KB  "
              f"PSNR {m['psnr']:5.2f}  s-PSNR {m['s_psnr']:5.2f}  "
              f"focal-PSNR {m['focal_psnr']:5.2f}")

    print(f"\n[6/6] Generating presentation figures -> {out_dir}")
    viz.plot_pipeline_overview(
        original_arr, saliency, level_field, composite.astype(np.uint8),
        sal_decoded, sal_size, out_dir / "fig00_pipeline_overview.png")
    viz.plot_saliency_analysis(
        original_arr, saliency, source, out_dir / "fig01_saliency_analysis.png")
    viz.plot_blur_pyramid(
        pyramid, cfg.sigma_step, out_dir / "fig02_blur_pyramid.png")
    viz.plot_level_field(
        original_arr, saliency, level_field, cfg.num_levels,
        out_dir / "fig03_level_field.png")
    viz.plot_composite_assembly(
        original_arr, composite.astype(np.uint8), level_field,
        out_dir / "fig04_composite_assembly.png")
    viz.plot_encoding_comparison(
        [metrics_baseline, metrics_eq, metrics_sal],
        out_dir / "fig05_encoding_comparison.png")

    # Rate-distortion sweep across qualities for both methods.
    print(f"      Sweeping rate-distortion (this is the slow step)...")
    rd = sweep_rate_distortion(image, original_arr, composite, saliency,
                                qualities=(20, 35, 50, 65, 80, 92))
    viz.plot_rate_distortion(rd, out_dir / "fig06_rate_distortion.png")

    print(f"\nDone. Open {out_dir} to view all figures and encoded files.")


def sweep_rate_distortion(image, original_arr, composite, saliency, qualities):
    rows_baseline = []
    rows_saliency = []
    for q in qualities:
        b_bytes = sc.encode_to_bytes(original_arr, fmt="JPEG", quality=q)
        s_bytes = sc.encode_to_bytes(composite, fmt="JPEG", quality=q)
        b_dec = np.asarray(Image.open(__import__("io").BytesIO(b_bytes)).convert("RGB"))
        s_dec = np.asarray(Image.open(__import__("io").BytesIO(s_bytes)).convert("RGB"))
        rows_baseline.append({
            "quality": q, "bytes": len(b_bytes),
            "psnr": sc.psnr(original_arr, b_dec),
            "s_psnr": sc.saliency_weighted_psnr(original_arr, b_dec, saliency),
            "focal_psnr": sc.focal_psnr(original_arr, b_dec, saliency),
        })
        rows_saliency.append({
            "quality": q, "bytes": len(s_bytes),
            "psnr": sc.psnr(original_arr, s_dec),
            "s_psnr": sc.saliency_weighted_psnr(original_arr, s_dec, saliency),
            "focal_psnr": sc.focal_psnr(original_arr, s_dec, saliency),
        })
    return {"Uniform JPEG": rows_baseline, "Saliency-aware JPEG": rows_saliency}


if __name__ == "__main__":
    main()
