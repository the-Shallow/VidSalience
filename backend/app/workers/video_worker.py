import time
from pathlib import Path
from app.model.job_model import JobStatus
from app.services.job_service import job_service
from app.services.r2_storage_service import r2_storage_service
from app.services.vidsalience_service import vidsalience_service

TEMP_DIR = Path("tmp/videos")
CHECKPOINT_PATH = "outputs/checkpoints/best.pth"
MODEL_R2_KEY = "models/best.pth"

def process_video_job(job_id:str):
    print(f"Processing job {job_id}...")

    job = job_service.get_job(job_id)

    if not job:
        print(f"Job {job_id} not found")
        return
    
    try:
        job_service.update_status(job_id, JobStatus.PROCESSING)

        # Simulate video processing
        # time.sleep(10)

        job_dir = TEMP_DIR / job_id
        input_path = job_dir / "input.mp4"
        output_path = job_dir / "saliency_output.mp4"

        r2_storage_service.download_file(object_key= job.input_object_key,
                                          local_path=str(input_path))


        checkpoint_path = r2_storage_service.ensure_file_downloaded(
            object_key=MODEL_R2_KEY,
            local_path=CHECKPOINT_PATH
        )
    
        metrics = vidsalience_service.process_video(
            input_path=str(input_path),
            output_path=str(output_path),
            checkpoint_path=checkpoint_path
        )

        output_key = f"processed/{job_id}/saliency_output.mp4"

        r2_storage_service.upload_local_file(
            local_path=str(output_path),
            object_key=output_key,
            content_type="video/mp4"
        )

        job_service.set_output_key(job_id, output_key)

        # print("Metrics:", metrics)

        job_service.set_metrics(job_id, metrics)

        # Update job status to COMPLETED
        job_service.update_status(job_id, JobStatus.COMPLETED)
        print(f"Job {job_id} completed successfully")

    except Exception as e:
        job_service.update_status(job_id, JobStatus.FAILED, error_message=str(e))
        raise
    