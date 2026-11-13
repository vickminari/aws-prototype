from fastapi import UploadFile

from app.services.storage.base import StorageService, read_image


class S3StorageService(StorageService):
    """S3 storage using the instance role in production."""

    def __init__(self, bucket: str, region: str) -> None:
        import boto3

        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    def upload(self, key: str, file: UploadFile) -> None:
        content, extension = read_image(file)
        content_types = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_types[extension],
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def get_url(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=3600,
        )
