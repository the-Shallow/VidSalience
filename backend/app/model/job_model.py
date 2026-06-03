from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class JobStatus(str, Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VideoJob(BaseModel):
    job_id: str
    original_filename: str
    input_object_key: str
    output_object_key: str | None = None
    status: JobStatus
    error_message: str | None = None
    metrics: dict | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)