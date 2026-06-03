import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.model.job_model import JobStatus
from app.services.job_service import job_service
from app.services.r2_storage_service import r2_storage_service
from app.services.queue_service import queue_service

router = APIRouter(prefix="/videos", tags=["videos"])

MAX_VIDEO_SIZE_MB = 200

ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/x-matroska",
    "video/webm",
    "video/avi",
    "video/mpeg",
}

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    if not file.content_type or file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported video format") 

    file.file.seek(0,2)
    file_size = file.file.tell()
    file.file.seek(0)

    # max_size_bytes = MAX_VIDEO_SIZE_MB * 1024 * 1024
    # if file_size > max_size_bytes:
    #     raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_VIDEO_SIZE_MB} MB limit")
    
    job_id = str(uuid.uuid4())
    input_object_key = f"uploads/{job_id}/{file.filename}"

    uploaded_key = await r2_storage_service.upload_file(
        file=file,
        object_key=input_object_key,
    )

    if not r2_storage_service.object_exists(uploaded_key):
        raise HTTPException(status_code=500, detail="Failed to upload video to storage")
    
    job = job_service.create_job(
        job_id=job_id,
        original_filename=file.filename,
        input_object_key=uploaded_key
    )

    queue_info = queue_service.enqueue_job(job_id)

    job_service.update_status(job_id, JobStatus.QUEUED)

    return {
        "message": "Video uploaded and job created successfully",
        "job_id": job_id,
        "queue_info": queue_info
    }


@router.get("/{job_id}")
def get_job(job_id:str):
    job = job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "COMPLETED":
        return {
            "job_id": job.job_id,
            "status": job.status,
            "message": "Job is still processing. Please check back later."
        }
    
    if not job.output_object_key:
        raise HTTPException(status_code=404, detail="Output video not found")
    
    download_url = r2_storage_service.generate_presigned_download_url(job.output_object_key)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "original_filename": job.original_filename,
        "input_object_key": job.input_object_key,
        "output_object_key": job.output_object_key,
        "download_url": download_url,
        "metrics": job.metrics
    }