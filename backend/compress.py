"""Saliency inference: load the trained model and predict, with a ground-truth
fallback so the compression pipeline is demoable before training finishes."""

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
import cv2
from PIL import Image
from torchvision import transforms
from collections import deque

from models.saliency_model import SaliencyModel

import subprocess
import os


def _load_model(checkpoint_path: str, device: torch.device) -> Optional[SaliencyModel]:
    # print(checkpoint_path)
    if checkpoint_path is None or not Path(checkpoint_path).exists():
        return None
    model = SaliencyModel(pretrained=False).to(device)
    state = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state["model_state_dict"])
    model.eval()
    return model


@torch.no_grad()
def predict_saliency(
    model, frame, device, image_size=(256,192)
) -> np.ndarray:
    """Return a saliency map in [0, 1] at the original image resolution.

    Uses the trained network if a checkpoint exists; otherwise raises so the
    caller can fall back to a ground-truth map for demonstration purposes.
    """
    
    orig_h,orig_w = frame.shape[:2]
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_frame)
    tfm = transforms.Compose([
        transforms.Resize(image_size),
        transforms.ToTensor(),
    ])
    x = tfm(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        sal = model(x)  # (1, 1, H', W'), normalized to sum=1
    # sal = torch.nn.functional.interpolate(
    #     sal, size=(orig_h, orig_w), mode="bilinear", align_corners=False
    # )
    sal = sal.squeeze().cpu().numpy()
    sal = cv2.resize(sal, (orig_w, orig_h))
    return _to_unit_range(sal)
    # sal = sal - sal.min()
    # sal = sal / (sal.max() + 1e-8)
    # return sal


def _to_unit_range(arr: np.ndarray) -> np.ndarray:
    arr = np.clip(arr, 0, None)
    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-12:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def apply_saliency_blur(frame, saliency, blur_strength=31):
    blurred = cv2.GaussianBlur(frame, (blur_strength, blur_strength),0)

    mask = saliency[...,None]

    output = frame * mask + blurred * (1 - mask)
    output = np.clip(output, 0 , 255).astype(np.uint8)

    return output


def create_baseline(input_video, output_video):
    Path(output_video).parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(input_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        writer.write(frame)

    cap.release()
    writer.release()


def get_saliency_bbox(saliency, threshold=0.6, padding=25, min_area_ratio=0.01):
    h,w = saliency.shape
    mask = saliency > threshold

    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return None
    
    x1 = max(int(xs.min()) - padding, 0)
    y1 = max(int(ys.min()) - padding, 0)
    x2 = min(int(xs.max()) + padding, w - 1)
    y2 = min(int(ys.max()) + padding, h - 1)

    box_area = (x2 - x1) * (y2 - y1)
    frame_area = w * h
    if box_area / frame_area < min_area_ratio:
        return None
    
    return x1, y1, x2, y2

def apply_roi_downsample_soft(frame, bbox, scale=0.40, feather=125):
    h, w = frame.shape[:2]

    small = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    degraded = cv2.resize(small, (w,h), interpolation=cv2.INTER_LINEAR)

    if bbox is None:
        return degraded
    
    x1, y1, x2, y2 = bbox

    mask = np.zeros((h,w), dtype=np.float32)
    mask[y1:y2, x1:x2] = 1.0

    feather = feather if feather % 2 == 1 else feather + 1
    mask = cv2.GaussianBlur(mask, (feather, feather), 0)

    mask = mask[..., None]

    # degraded[y1:y2, x1:x2] = frame[y1:y2, x1:x2]
    output = frame * mask + degraded * (1 - mask)
    return np.clip(output, 0, 255).astype(np.uint8)


def smooth_bbox(bbox_history):
    valid_boxes = [box for box in bbox_history if box is not None]
    if len(valid_boxes) == 0:
        return None
    
    avg_bbox = np.mean(valid_boxes, axis=0)
    return tuple(int(v) for v in avg_bbox)


def encode_browser_ready_mp4(temp_video, output_video, crf=30):
    """
    Convert OpenCV-written video into browser-compatible H.264 MP4.
    """
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", temp_video,
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_video
    ], check=True)

    if os.path.exists(temp_video):
        os.remove(temp_video)


def compute_segment_roi(video_path, model, device, image_size=(256,192), threshold=0.6, padding=25, max_frames=30):
    cap = cv2.VideoCapture(str(video_path))
    saliency_maps = []
    frame_count = 0

    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        saliency = predict_saliency(model, frame, device, image_size)
        saliency_maps.append(saliency)
        frame_count += 1

    cap.release()

    if len(saliency_maps) == 0:
        return None
    
    avg_saliency = np.mean(saliency_maps, axis=0)
    bbox = get_saliency_bbox(avg_saliency, threshold=threshold, padding=padding)

    if bbox is None:
        return None
    
    x1, y1, x2, y2 = bbox

    return {
        "x": x1,
        "y": y1,
        "w": x2 - x1,
        "h": y2 - y1
    }


def split_video_into_segments(input_video, segments_dir, segment_duration=2):
    segments_dir = Path(segments_dir)
    segments_dir.mkdir(parents=True, exist_ok=True)

    segment_pattern = segments_dir / "segment_%03d.mp4"

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", str(input_video),
        "-c", "copy",
        "-map", "0",
        "-segment_time", str(segment_duration),
        "-f", "segment",
        "-reset_timestamps", "1",
        str(segment_pattern)
    ], check=True)

    return sorted(segments_dir.glob("segment_*.mp4"))

def encode_segment_with_addroi(segment_path, output_path, roi, crf=32, qoffset=-0.1):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if roi is None:
        vf_filter = "null"
    else:
        x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
        vf_filter = f"addroi=x={x}:y={y}:w={w}:h={h}:qoffset={qoffset}"

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", str(segment_path),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path)
    ], check=True)


def encode_all_segments_with_dynamic_roi(segments, encoded_dir, model, device, image_size=(256, 192), threshold=0.6, padding=25, crf=32, qoffset=-0.1):
    encoded_dir = Path(encoded_dir)
    encoded_dir.mkdir(parents=True, exist_ok=True)

    encoded_segments = []

    for idx, segment_path in enumerate(segments):
        print(f"Processing segment {idx+1}/{len(segments)}: {segment_path.name}")
        roi = compute_segment_roi(segment_path, model, device, image_size=image_size, threshold=threshold, padding=padding)
        print("ROI:", roi)
        encoded_path = encoded_dir / f"encoded_{idx:03d}.mp4"
        encode_segment_with_addroi(segment_path, encoded_path, roi, crf=crf, qoffset=qoffset)
        encoded_segments.append(encoded_path)

    return encoded_segments

def concat_encoded_segments(encoded_segments, output_video):
    output_video = Path(output_video)
    output_video.parent.mkdir(parents=True, exist_ok=True)

    list_file = output_video.parent / "concat_list.txt"

    with open(list_file, "w", encoding="utf-8") as f:
        for segment in encoded_segments:
            segment_path = Path(segment).resolve()
            f.write(f"file '{segment_path.as_posix()}'\n")

    
    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_video)
    ], check=True)

    if list_file.exists():
        list_file.unlink()


def compress_video_with_dynamic_roi(
        input_video,
        output_video,
        checkpoint_path,
        image_size=(256,192),
        segment_duration=2,
        threshold=0.6,
        padding=25,
        crf=32,
        qoffset=-0.1,
):
    output_path = Path(output_video)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    work_dir = output_path.parent / "dynamic_roi_work"
    segments_dir = work_dir / "segments"
    encoded_dir = work_dir / "encoded_segments"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = _load_model(checkpoint_path, device)

    if model is None:
        raise FileNotFoundError(f"Could not load checkpoint: {checkpoint_path}")

    print("Splitting video...")

    segments = split_video_into_segments(
        input_video, segments_dir, segment_duration=segment_duration
    )

    print("Encoding segments with dynamic ROI...")
    encoded_segmnents = encode_all_segments_with_dynamic_roi(
        segments, encoded_dir, model, device, image_size=image_size, threshold=threshold, padding=padding, crf=crf, qoffset=qoffset
    )

    print("Concatenating final video...")
    concat_encoded_segments(encoded_segmnents, output_video)

    print(f"Dynamic ROI video saved to: {output_path}")

def compress_video_with_saliency(
    input_video,
    output_video,
    checkpoint_path,
    image_size=(256,192),
    blur_strength=31
):
    Path(output_video).parent.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(checkpoint_path)
    model = _load_model(checkpoint_path,device)
    print("Model loaded:", model is not None)
    cap = cv2.VideoCapture(input_video)

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


    output_path = Path(output_video)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_path.with_name(output_path.stem + "_temp.mp4")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v") 
    writer = cv2.VideoWriter(str(temp_output), fourcc, fps, (width,height))


    print(f"Processing video: {input_video}")

    saliency_history = deque(maxlen=5)
    bbox_history = deque(maxlen=5)

    while True:
        # print("Reading frame...")
        ret, frame = cap.read()
        if not ret:
            break

        current_saliency = predict_saliency(model, frame, device, image_size)
        saliency_history.append(current_saliency)
        saliency = np.mean(saliency_history, axis=0)
        # bbox = smooth_bbox(bbox_history)

        bbox = get_saliency_bbox(saliency)
        # print("Saliency bbox:", bbox)

        bbox_history.append(bbox)

        smoothed_bbox = smooth_bbox(bbox_history)
        # compressed_frame = apply_saliency_blur(frame, saliency, blur_strength)
        compressed_frame = apply_roi_downsample_soft(frame, smoothed_bbox)

        writer.write(compressed_frame)

    cap.release()
    writer.release()
    encode_browser_ready_mp4(str(temp_output), str(output_video), crf=32)