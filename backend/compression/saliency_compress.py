"""Saliency-guided image compression producing a single standard-format file.

Pipeline
--------
1. Build a multi-level low-pass pyramid of the input (sharp -> blurry).
2. Map normalized saliency in [0,1] to a continuous pyramid index in [0, N-1].
   High saliency selects sharp levels; low saliency selects blurry levels.
3. Composite per-pixel using bilinear interpolation between adjacent levels
   (smooth so there are no visible quality boundaries).
4. Encode the composite with a standard codec (JPEG by default).

Why this saves bits: any DCT-based codec (JPEG, WebP, AVIF, HEIC) spends most
of its bits on high-frequency coefficients. Pre-blurring low-saliency regions
zeros out those coefficients before the encoder ever sees them, so the same
quality factor produces a much smaller file -- with no loss of detail in the
regions a viewer will actually look at.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image


@dataclass
class CompressionConfig:
    num_levels: int = 6            # pyramid depth (level 0 = sharp, N-1 = blurriest)
    sigma_step: float = 1.1        # Gaussian sigma multiplier per level
    sharp_threshold: float = 0.45  # saliency >= this is locked to level 0 (full detail)
    saliency_gamma: float = 0.7    # <1 expands the high-saliency region (more sharp area)
    saliency_floor: float = 0.0    # min normalized saliency before mapping (clamps lows up)
    saliency_ceiling: float = 1.0  # max
    smooth_saliency_sigma: float = 6.0  # blur the saliency map itself for soft transitions
    jpeg_quality: int = 75
    webp_quality: int = 75


def build_blur_pyramid(image: np.ndarray, num_levels: int, sigma_step: float) -> List[np.ndarray]:
    """Return [sharpest, ..., blurriest]. Level 0 is the original."""
    pyramid = [image.astype(np.float32)]
    for i in range(1, num_levels):
        sigma = sigma_step * i
        ksize = int(2 * round(3 * sigma) + 1)  # cover ~3 sigma each side
        blurred = cv2.GaussianBlur(image, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)
        pyramid.append(blurred.astype(np.float32))
    return pyramid


def saliency_to_level_field(
    saliency: np.ndarray,
    num_levels: int,
    cfg: CompressionConfig,
) -> np.ndarray:
    """Map saliency [0,1] -> per-pixel pyramid index in [0, N-1].

    High saliency -> 0 (sharp). Low saliency -> N-1 (blurry).
    """
    s = np.clip(saliency, cfg.saliency_floor, cfg.saliency_ceiling)
    s = (s - cfg.saliency_floor) / max(cfg.saliency_ceiling - cfg.saliency_floor, 1e-8)

    # Smooth first so quality boundaries don't ring; then re-normalize so the
    # peak still hits 1.0 (otherwise the most-salient pixel never reaches the
    # sharp pyramid level).
    if cfg.smooth_saliency_sigma > 0:
        ksize = int(2 * round(3 * cfg.smooth_saliency_sigma) + 1)
        s = cv2.GaussianBlur(s.astype(np.float32), (ksize, ksize),
                             sigmaX=cfg.smooth_saliency_sigma)
        peak = float(s.max())
        if peak > 1e-8:
            s = s / peak

    # Sharp-zone clamp: saliency above the threshold is treated as fully
    # salient. Below the threshold we scale linearly into [0, 1] so the
    # transition is continuous.
    s = np.clip(s, 0, 1)
    if cfg.sharp_threshold > 0:
        s = np.minimum(1.0, s / cfg.sharp_threshold)

    # Gamma reshapes the falloff. gamma<1 expands the high-saliency region.
    s = np.power(s, cfg.saliency_gamma)

    return (1.0 - s) * (num_levels - 1)


def composite_pyramid(pyramid: List[np.ndarray], level_field: np.ndarray) -> np.ndarray:
    """Blend pyramid levels per pixel using a continuous level index field."""
    n = len(pyramid)
    lower = np.floor(level_field).astype(np.int32)
    lower = np.clip(lower, 0, n - 1)
    upper = np.clip(lower + 1, 0, n - 1)
    frac = (level_field - lower).astype(np.float32)[..., None]  # (H, W, 1)

    h, w = level_field.shape
    out = np.zeros_like(pyramid[0])
    for i in range(n):
        mask_low = (lower == i)[..., None]
        mask_up = (upper == i)[..., None]
        weight = mask_low * (1.0 - frac) + mask_up * frac
        out += pyramid[i] * weight
    return np.clip(out, 0, 255)


def encode_image(
    image_array: np.ndarray,
    output_path: str | Path,
    fmt: str = "JPEG",
    quality: int = 75,
) -> int:
    """Save and return the file size in bytes."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(image_array.astype(np.uint8))
    save_kwargs = {"quality": quality}
    if fmt.upper() == "JPEG":
        save_kwargs["optimize"] = True
        save_kwargs["progressive"] = True
    img.save(output_path, fmt, **save_kwargs)
    return output_path.stat().st_size


def encode_to_bytes(image_array: np.ndarray, fmt: str = "JPEG", quality: int = 75) -> bytes:
    buf = BytesIO()
    img = Image.fromarray(image_array.astype(np.uint8))
    save_kwargs = {"quality": quality}
    if fmt.upper() == "JPEG":
        save_kwargs["optimize"] = True
        save_kwargs["progressive"] = True
    img.save(buf, fmt, **save_kwargs)
    return buf.getvalue()


def saliency_compress(
    image: Image.Image,
    saliency: np.ndarray,
    cfg: Optional[CompressionConfig] = None,
) -> Tuple[np.ndarray, dict]:
    """Run the full pipeline and return (composite_array, intermediates).

    intermediates keys: 'pyramid' (list of arrays), 'level_field' (HxW float).
    """
    if cfg is None:
        cfg = CompressionConfig()

    arr = np.asarray(image.convert("RGB"))
    pyramid = build_blur_pyramid(arr, cfg.num_levels, cfg.sigma_step)
    level_field = saliency_to_level_field(saliency, cfg.num_levels, cfg)
    composite = composite_pyramid(pyramid, level_field)
    return composite, {"pyramid": pyramid, "level_field": level_field, "config": cfg}


# ---------- Comparison utilities ----------

def psnr(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    mse = np.mean((a - b) ** 2)
    if mse <= 1e-12:
        return float("inf")
    return float(10.0 * np.log10((255.0 ** 2) / mse))


def saliency_weighted_psnr(a: np.ndarray, b: np.ndarray, saliency: np.ndarray) -> float:
    """PSNR weighted so errors in salient regions count more."""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    w = saliency.astype(np.float64)
    w = w / (w.sum() + 1e-12)
    sq_err = np.mean((a - b) ** 2, axis=-1) if a.ndim == 3 else (a - b) ** 2
    weighted_mse = float((w * sq_err).sum())
    if weighted_mse <= 1e-12:
        return float("inf")
    return 10.0 * np.log10((255.0 ** 2) / weighted_mse)


def focal_psnr(a: np.ndarray, b: np.ndarray, saliency: np.ndarray,
               top_fraction: float = 0.2) -> float:
    """PSNR computed only over the top-K% most salient pixels.

    Closer to the human-perceptual question "how good does the focal region
    look?" than a smooth saliency-weighted PSNR, which is dragged down by
    a long tail of mildly-salient pixels.
    """
    a = a.astype(np.float64); b = b.astype(np.float64)
    threshold = np.quantile(saliency, 1.0 - top_fraction)
    mask = saliency >= threshold
    if a.ndim == 3:
        sq_err = ((a - b) ** 2).mean(axis=-1)
    else:
        sq_err = (a - b) ** 2
    mse = float(sq_err[mask].mean())
    if mse <= 1e-12:
        return float("inf")
    return 10.0 * np.log10((255.0 ** 2) / mse)


def encode_to_target_size(
    image_array: np.ndarray,
    target_bytes: int,
    fmt: str = "JPEG",
    tolerance: float = 0.03,
) -> Tuple[bytes, int]:
    """Binary-search the quality knob until file size lands near target.

    Used to make a fair, equal-bitrate visual comparison against the saliency
    output. Returns (encoded_bytes, quality_used).
    """
    lo, hi = 5, 95
    best = None
    best_err = float("inf")
    for _ in range(10):
        q = (lo + hi) // 2
        data = encode_to_bytes(image_array, fmt=fmt, quality=q)
        size = len(data)
        err = abs(size - target_bytes) / target_bytes
        if err < best_err:
            best_err = err
            best = (data, q, size)
        if err < tolerance:
            return data, q
        if size > target_bytes:
            hi = q - 1
        else:
            lo = q + 1
        if lo > hi:
            break
    return best[0], best[1]
