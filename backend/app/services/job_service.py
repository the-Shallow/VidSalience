from datetime import datetime
from app.db import jobs_collection
from app.model.job_model import VideoJob, JobStatus

class JobService:
    def create_job(self, job_id:str, original_filename:str, input_object_key:str):
        job = VideoJob(
            job_id=job_id,
            original_filename=original_filename,
            input_object_key=input_object_key,
            status=JobStatus.UPLOADED
        )

        jobs_collection.insert_one(job.model_dump())
        return job
    
    def get_job(self, job_id:str):
        doc = jobs_collection.find_one(
            {"job_id": job_id},
            {"_id": 0}
        )

        if not doc:
            return None
        
        return VideoJob(**doc)
    
    def update_status(self, job_id:str, status:JobStatus, error_message: str | None = None):
        jobs_collection.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow(),
                    "error_message": error_message
                }
            }
        )

        return self.get_job(job_id)
    
    def set_output_key(self, job_id:str, output_object_key:str):
        jobs_collection.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "output_object_key": output_object_key,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return self.get_job(job_id)
    
    def set_metrics(self, job_id:str, metrics:dict):
        jobs_collection.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "metrics": metrics,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return self.get_job(job_id)
    

job_service = JobService()