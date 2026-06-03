from redis import Redis
from rq import Queue

from app.config import settings

class QueueService:
    def __init__(self):
        self.redis_conn = Redis.from_url(settings.REDIS_URL)
        self.queue = Queue("video-processing", connection=self.redis_conn)

    def enqueue_job(self, job_id:str):
        job = self.queue.enqueue("app.workers.video_worker.process_video_job",
                                    job_id,
                                    job_timeout="30m",
                                    result_ttl=86400,
                                    failure_ttl=86400)
        return {
            "rq_job_id": job.id,
            "job_id": job_id,
            "queue": "video-processing"
        }
        

queue_service = QueueService()