from training.train import train
from compress import compress_video_with_dynamic_roi, compress_video_with_saliency, create_baseline

if __name__ == "__main__":
    # train()

    # create_baseline(
    #     input_video="input_video_2.mp4",
    #     output_video="outputs/baseline_compressed.mp4"
    # )

    # compress_video_with_saliency(
    #     input_video="D:\\Projects\\VidSalience\\input_video_2.mp4",
    #     output_video="outputs/saliency_compressed.mp4",
    #     checkpoint_path="outputs\\checkpoints\\best.pth",
    #     image_size=(256,192),
    #     blur_strength=21
    # )

    compress_video_with_dynamic_roi(
        input_video="D:\\Projects\\VidSalience\\VID_2.mp4",
        output_video="outputs/dynamic_roi_final.mp4",
        checkpoint_path="outputs/checkpoints/best.pth",
        image_size=(256, 192),
        segment_duration=2,
        threshold=0.6,
        padding=25,
        crf=32,
        qoffset=-0.1,
    )