from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings


class StorageNotConfigured(RuntimeError):
    pass


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        if not (
            settings.s3_endpoint_url
            and settings.s3_access_key_id
            and settings.s3_access_key_id.get_secret_value().strip()
            and settings.s3_secret_access_key
            and settings.s3_secret_access_key.get_secret_value().strip()
        ):
            raise StorageNotConfigured("S3-compatible object storage is not fully configured.")
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        )

    def put(self, key: str, body: bytes, content_type: str) -> None:
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType=content_type)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("Could not store the uploaded report.") from exc

    def get(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("Could not read the stored report.") from exc


@lru_cache
def get_object_storage() -> ObjectStorage:
    return ObjectStorage(get_settings())
