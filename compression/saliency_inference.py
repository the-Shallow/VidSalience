"""Saliency inference: load the trained model and predict, with a ground-truth
fallback so the compression pipeline is demoable before training finishes."""

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from models.saliency_model import SaliencyModel


def _load_model(checkpoint_path: Optional[str], device: torch.device) -> Optional[SaliencyModel]:
    if checkpoint_path is None or not Path(checkpoint_path).exists():
        return None
    model = SaliencyModel(pretrained=False).to(device)
    state = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state["model_state_dict"])
    model.eval()
    return model


@torch.no_grad()
def predict_saliency(
    image: Image.Image,
    checkpoint_path: Optional[str] = "outputs/checkpoints/best.pth",
    image_size: Tuple[int, int] = (256, 192),
    device: Optional[torch.device] = None,
) -> np.ndarray:
    """Return a saliency map in [0, 1] at the original image resolution.

    Uses the trained network if a checkpoint exists; otherwise raises so the
    caller can fall back to a ground-truth map for demonstration purposes.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = _load_model(checkpoint_path, device)
    if model is None:
        raise FileNotFoundError(
            f"No checkpoint at {checkpoint_path}. "
            "Provide one or use load_ground_truth_map() for demos."
        )

    orig_w, orig_h = image.size
    tfm = transforms.Compose([
        transforms.Resize(image_size),
        transforms.ToTensor(),
    ])
    x = tfm(image.convert("RGB")).unsqueeze(0).to(device)

    sal = model(x)  # (1, 1, H', W'), normalized to sum=1
    sal = torch.nn.functional.interpolate(
        sal, size=(orig_h, orig_w), mode="bilinear", align_corners=False
    )
    sal = sal.squeeze().cpu().numpy()
    return _to_unit_range(sal)


def load_ground_truth_map(map_path: str, target_size: Tuple[int, int]) -> np.ndarray:
    """Load a SALICON GT map and return it in [0, 1] at target (W, H)."""
    sal = Image.open(map_path).convert("L").resize(target_size, Image.BILINEAR)
    arr = np.asarray(sal, dtype=np.float32)
    return _to_unit_range(arr)


def _to_unit_range(arr: np.ndarray) -> np.ndarray:
    arr = np.clip(arr, 0, None)
    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-12:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def get_saliency_map(
    image: Image.Image,
    checkpoint_path: str = "outputs/checkpoints/best.pth",
    gt_map_path: Optional[str] = None,
) -> Tuple[np.ndarray, str]:
    """Convenience wrapper. Tries the model first; falls back to GT.

    Returns (saliency_map, source_label).
    """
    try:
        sal = predict_saliency(image, checkpoint_path=checkpoint_path)
        return sal, "model"
    except FileNotFoundError:
        if gt_map_path is None:
            raise
        sal = load_ground_truth_map(gt_map_path, image.size)
        return sal, "ground-truth"
