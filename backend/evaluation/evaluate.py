import cv2
import os
import math
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from skimage.metrics import structural_similarity as ssim


import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

# from models.saliency_model import SaliencyModel
from compress import predict_saliency, _load_model


def get_file_size_mb(path):
    size_bytes = os.path.getsize(path)
    return size_bytes / (1024 * 1024)

def get_video_info(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    duration = frame_count / fps if fps > 0 else 0

    cap.release()

    return {
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration": duration
    }


def calculate_bitrate_kbps(video_path):
    size_bits = os.path.getsize(video_path) * 8
    info = get_video_info(video_path)

    if info["duration"] == 0:
        return 0
    
    bitrate_kbps = size_bits / info["duration"] / 1000
    return bitrate_kbps

def calculate_psnr(original_frame, compressed_frame):
    original = original_frame.astype(np.float32)
    compressed = compressed_frame.astype(np.float32)

    mse = np.mean((original - compressed) ** 2)
    if mse == 0:
        return float("inf")
    
    psnr = 20 * math.log10(255.0 / math.sqrt(mse))
    return psnr

def calculate_ssim(original_frame, compressed_frame):
    original_gray = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
    compressed_gray = cv2.cvtColor(compressed_frame, cv2.COLOR_BGR2GRAY)

    score = ssim(original_gray, compressed_gray, data_range=255)
    return score

def calculate_saliency_weighted_psnr(original_frame, compressed_frame, saliency):
    original = original_frame.astype(np.float32)
    compressed = compressed_frame.astype(np.float32)

    error = (original - compressed) ** 2
    saliency_3d = saliency[..., None]

    weighted_mse = np.sum(error * saliency_3d) / (np.sum(saliency_3d) * 3 + 1e-8)

    if weighted_mse == 0:
        return float("inf")
    
    weighted_psnr = 20 * math.log10(255.0 / math.sqrt(weighted_mse))
    return weighted_psnr

def evaluate_video_quality(original_video_path, compressed_video_path, checkpoint_path=None, image_size=(256,192), max_frames=None):
    cap_original = cv2.VideoCapture(original_video_path)
    cap_compressed = cv2.VideoCapture(compressed_video_path)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = None
    if checkpoint_path is not None:
        model = _load_model(checkpoint_path, device)

    psnr_scores = []
    ssim_scores = []
    saliency_weighted_psnr_scores = []

    frame_idx = 0

    while True:
        ret_original, original_frame = cap_original.read()
        ret_compressed, compressed_frame = cap_compressed.read()

        if not ret_original or not ret_compressed:
            break

        if original_frame.shape != compressed_frame.shape:
            compressed_frame = cv2.resize(
                compressed_frame,
                (original_frame.shape[1], original_frame.shape[0])
            )

        psnr_value = calculate_psnr(original_frame, compressed_frame)
        ssim_value = calculate_ssim(original_frame, compressed_frame)
        
        psnr_scores.append(psnr_value)
        ssim_scores.append(ssim_value)

        if model is not None:
            saliency = predict_saliency(model, original_frame, device, image_size)
            sw_psnr = calculate_saliency_weighted_psnr(
                original_frame,
                compressed_frame,
                saliency
            )
            saliency_weighted_psnr_scores.append(sw_psnr)

        frame_idx += 1

        if max_frames is not None and frame_idx >= max_frames:
            break

    cap_original.release()
    cap_compressed.release()


    results = {
        "average_psnr": float(np.mean(psnr_scores)),
        "average_ssim": float(np.mean(ssim_scores)),
        "frames_evaluated": frame_idx
    }

    if saliency_weighted_psnr_scores:
        results["average_saliency_weighted_psnr"] = float(
            np.mean(saliency_weighted_psnr_scores)
        )

    return results

def compare_videos(original_video, baseline_video, saliency_video, checkpoint_path, image_size=(256, 192), max_frames=None):
    original_size = get_file_size_mb(original_video)
    baseline_size = get_file_size_mb(baseline_video)
    saliency_size = get_file_size_mb(saliency_video)

    baseline_bitrate = calculate_bitrate_kbps(baseline_video)
    saliency_bitrate = calculate_bitrate_kbps(saliency_video)

    baseline_quality = evaluate_video_quality(
        original_video,
        baseline_video,
        checkpoint_path=checkpoint_path,
        image_size=image_size,
        max_frames=max_frames
    )

    saliency_quality = evaluate_video_quality(
        original_video,
        saliency_video,
        checkpoint_path=checkpoint_path,
        image_size=image_size,
        max_frames=max_frames
    )

    size_reduction_baseline = (
        (baseline_size - saliency_size) / baseline_size
    ) * 100

    bitrate_reduction_baseline = (
        (baseline_bitrate - saliency_bitrate) / baseline_bitrate
    ) * 100

    print("\n========== VIDEO COMPRESSION EVALUATION ==========\n")

    print("Original Video:")
    print(f"  Size: {original_size:.2f} MB")

    print("\nBaseline Compressed Video:")
    print(f"  Size: {baseline_size:.2f} MB")
    print(f"  Bitrate: {baseline_bitrate:.2f} kbps")
    print(f"  PSNR: {baseline_quality['average_psnr']:.2f}")
    print(f"  SSIM: {baseline_quality['average_ssim']:.4f}")
    print(f"  Saliency-weighted PSNR: {baseline_quality['average_saliency_weighted_psnr']:.2f}")

    print("\nSaliency Compressed Video:")
    print(f"  Size: {saliency_size:.2f} MB")
    print(f"  Bitrate: {saliency_bitrate:.2f} kbps")
    print(f"  PSNR: {saliency_quality['average_psnr']:.2f}")
    print(f"  SSIM: {saliency_quality['average_ssim']:.4f}")
    print(f"  Saliency-weighted PSNR: {saliency_quality['average_saliency_weighted_psnr']:.2f}")

    print("\nComparison:")
    print(f"  Size reduction vs baseline: {size_reduction_baseline:.2f}%")
    print(f"  Bitrate reduction vs baseline: {bitrate_reduction_baseline:.2f}%")
    print(f"  PSNR change: {saliency_quality['average_psnr'] - baseline_quality['average_psnr']:.2f}")
    print(f"  SSIM change: {saliency_quality['average_ssim'] - baseline_quality['average_ssim']:.4f}")
    print(
        "  Saliency-weighted PSNR change: "
        f"{saliency_quality['average_saliency_weighted_psnr'] - baseline_quality['average_saliency_weighted_psnr']:.2f}"
    )

    print("\n=================================================\n")



if __name__ == "__main__":
    compare_videos(
        original_video="D:\\Projects\\VidSalience\\VID_2.mp4",
        baseline_video="D:\\Projects\\VidSalience\\ffmpeg_only_crf32.mp4",
        saliency_video="outputs/dynamic_roi_final.mp4",
        checkpoint_path="outputs\\checkpoints\\best.pth",
        image_size=(256,192),
        max_frames=300
    )