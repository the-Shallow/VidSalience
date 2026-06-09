# VidSalience: Saliency-Aware Video Compression

VidSalience is a saliency-aware video compression system that reduces video size while trying to preserve visual quality in the most important regions of a video. Instead of compressing every part of a frame equally, the system uses a neural network-based saliency model to identify visually important regions and applies stronger compression to less important background areas.

The project includes a complete web-based pipeline where users can upload a video, process it through a backend queue, store compressed outputs in cloud storage, and download the final result.

---

## Overview

Traditional video compression methods such as FFmpeg-based CRF compression apply compression globally across the entire video. This can reduce file size effectively, but it does not understand which parts of the frame are visually more important to a viewer.

VidSalience adds a saliency-guided layer on top of standard video compression. It generates saliency maps for video frames, uses those maps to identify important regions, and applies region-aware processing before final encoding.

The goal is not to replace FFmpeg, but to use neural-network-based saliency information to guide compression more intelligently.

---

## Key Features

- Upload video through a web interface
- Queue-based asynchronous video processing
- Neural network-based saliency map generation
- Saliency-guided video compression
- FFmpeg-based final encoding
- Cloudflare R2 storage integration
- MongoDB job/status tracking
- Redis Queue worker for background processing
- Dockerized backend deployment
- REST API built with FastAPI

---

## System Architecture

```text
User Uploads Video
        |
        v
Frontend Application
        |
        v
FastAPI Backend
        |
        v
Cloudflare R2 Storage
        |
        v
Redis Queue Job Created
        |
        v
Worker Downloads Video
        |
        v
Saliency Model Generates Maps
        |
        v
Saliency-Guided Compression
        |
        v
FFmpeg Final Encoding
        |
        v
Compressed Video Uploaded to R2
        |
        v
Frontend Shows Result
```

---

## Tech Stack

### Frontend

- React
- Vite
- TypeScript
- TanStack Query

### Backend

- FastAPI
- Python
- Redis Queue / RQ
- MongoDB Atlas
- Cloudflare R2
- Docker
- FFmpeg

### Machine Learning / Video Processing

- PyTorch
- VGG-based + UNet Arch
- OpenCV
- FFmpeg

### Deployment

- AWS EC2
- Docker Compose
- Cloudflare R2 for object storage
- MongoDB Atlas for metadata

---

## How It Works

### 1. Video Upload

The user uploads a video from the frontend. The backend receives the video and uploads the original file to Cloudflare R2.

### 2. Job Creation

After upload, the backend creates a processing job in MongoDB and pushes the task to a Redis queue.

### 3. Background Processing

A worker process picks up the job from Redis. The worker downloads the original video from R2 and starts processing it.

### 4. Saliency Map Generation

The video is split into frames or segments. A trained saliency model predicts which parts of the frame are visually important.

### 5. Saliency-Guided Compression

Important regions are preserved with higher quality, while less important background areas can be compressed more aggressively.

### 6. Final Encoding

FFmpeg is used to encode the processed video into a compressed output format.

### 7. Result Upload

The compressed video is uploaded back to Cloudflare R2. The job status is updated in MongoDB, and the frontend displays the result.

---

## Why FFmpeg Is Still Used

VidSalience depends on FFmpeg for low-level video encoding, decoding, and final compression. FFmpeg is not the main novelty of the project; it acts as the encoding engine.

The core project contribution is the saliency-aware decision layer that guides how the video should be processed before encoding.
---


<!-- ## Evaluation

The system can be evaluated using:

- Output file size
- Compression ratio
- PSNR
- SSIM
- Saliency-weighted PSNR
- Visual comparison of important regions

Example metrics from earlier experiments:

```text
Original Video Size: 22.14 MB

Baseline Compressed Video:
  Size: 26.62 MB
  PSNR: 38.76
  SSIM: 0.9801

Saliency Compressed Video:
  Size: 19.56 MB
  PSNR: 34.90
  SSIM: 0.9524

Size Reduction vs Baseline: 26.52%
```

These results show that saliency-aware compression can reduce file size compared to a baseline, while still maintaining reasonable visual quality.

--- -->
