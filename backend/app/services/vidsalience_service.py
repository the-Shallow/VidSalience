from pathlib import Path
from compress import compress_video_with_saliency, compress_video_with_dynamic_roi
from evaluation.evaluate import evaluate_video_quality, get_file_size_mb, calculate_bitrate_kbps


class VidSalienceService:
    def process_video(self, input_path:str, output_path:str, checkpoint_path:str):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        compress_video_with_dynamic_roi(
            input_video=input_path,
            output_video=output_path,
            checkpoint_path=checkpoint_path,
            image_size=(256,192),
            segment_duration=2,
            threshold=0.6,
            padding=25,
            crf=32,
            qoffset=-0.1,
        )

        # compress_video_with_saliency(
        #     input_video=input_path,
        #     output_video=output_path,
        #     checkpoint_path=checkpoint_path,
        #     image_size=(256,192),
        #     blur_strength=31
        # )

        metrics = evaluate_video_quality(
            original_video_path=input_path,
            compressed_video_path=output_path,
            checkpoint_path=checkpoint_path,
            image_size=(256,192),
            max_frames=300
        )

        metrics["original_size_mb"] = get_file_size_mb(input_path)
        metrics["compressed_size_mb"] = get_file_size_mb(output_path)
        metrics["compressed_bitrate_kbps"] = calculate_bitrate_kbps(output_path)

        return metrics


vidsalience_service = VidSalienceService()