from app.core.config import Settings
from app.services.storage.base import StorageService
from app.services.storage.local import LocalStorageService
from app.services.storage.s3 import S3StorageService


def create_storage(settings: Settings) -> StorageService:
    if settings.storage_backend == "local":
        return LocalStorageService()
    if settings.s3_bucket is None:
        raise ValueError("S3_BUCKET é obrigatório quando STORAGE_BACKEND=s3")
    return S3StorageService(settings.s3_bucket, settings.aws_region)


__all__ = ["StorageService", "LocalStorageService", "S3StorageService", "create_storage"]
