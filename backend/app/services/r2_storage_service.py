from pathlib import Path

import boto3
from botocore.client import ClientError, Config
from fastapi import UploadFile
from boto3.s3.transfer import TransferConfig
from app.config import settings


class R2StorageService:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.CLOUDFARE_ACC_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.CLOUDFLARE_ACCESS_KEY,
            aws_secret_access_key=settings.CLOUDFLARE_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

        self.multipart_config = TransferConfig(
            multipart_threshold=25 * 1024 * 1024,
            multipart_chunksize=25 * 1024 * 1024,
            max_concurrency=4,
            use_threads=True
        )

        self.bucket = settings.R2_BUCKET_NAME


    async def upload_file(self, file:UploadFile, object_key:str):
        self.client.upload_fileobj(
            file.file,
            self.bucket,
            object_key,
            ExtraArgs={
                "ContentType": file.content_type or "application/octet-stream"
            }
        )

        return object_key
    
    def object_exists(self, object_key:str):
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=object_key
            )
            return True
        except ClientError:
            return False
    
    def generate_presigned_download_url(self, object_key:str, expires_in:int = 3600):
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": object_key
            },
            ExpiresIn=expires_in
        )


    def upload_local_file(self, local_path:str, object_key:str, content_type:str = "video/mp4"):
        self.client.upload_file(
            local_path,
            self.bucket,
            object_key,
            ExtraArgs={
                "ContentType": content_type
            },
            Config=self.multipart_config
        )

        return object_key
    
    
    def download_file(self, object_key: str, local_path: str):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(
            self.bucket,
            object_key,
            local_path
        )

        return local_path
    
    def ensure_file_downloaded(self, object_key:str, local_path:str):
        local_path = Path(local_path)
        if local_path.exists():
            return str(local_path)
        
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(
            self.bucket,
            object_key,
            str(local_path)
        )

        return str(local_path)
    
    def delete_file(self, object_key:str):
        self.client.delete_object(
            Bucket=self.bucket,
            Key=object_key
        )


r2_storage_service = R2StorageService()