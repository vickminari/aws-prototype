from abc import ABC, abstractmethod

from fastapi import UploadFile

MAX_IMAGE_BYTES = 2 * 1024 * 1024
IMAGE_SIGNATURES = {
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "webp": (b"RIFF",),
}


def read_image(file: UploadFile) -> tuple[bytes, str]:
    """Read and validate an image using its binary signature."""
    content = file.file.read(MAX_IMAGE_BYTES + 1)
    file.file.seek(0)
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("image too large")

    if content.startswith(IMAGE_SIGNATURES["jpeg"]):
        extension = "jpg"
    elif content.startswith(IMAGE_SIGNATURES["png"]):
        extension = "png"
    elif content.startswith(IMAGE_SIGNATURES["webp"]) and content[8:12] == b"WEBP":
        extension = "webp"
    else:
        raise ValueError("invalid image signature")
    return content, extension


class StorageService(ABC):
    """Interface for storage backends (local filesystem or S3)."""

    @abstractmethod
    def upload(self, key: str, file: UploadFile) -> None:
        """Store the uploaded file under the given *key*.
        Should raise an ``HTTPException`` with status 422 on validation errors.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete the object identified by *key* (missing objects are ignored)."""

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Return a public (or pre‑signed) URL for the stored object.
        For the local backend this is a relative path under ``/api/media``.
        """
