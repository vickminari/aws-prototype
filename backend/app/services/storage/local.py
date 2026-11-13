from pathlib import Path

from fastapi import UploadFile

from app.services.storage.base import StorageService, read_image


class LocalStorageService(StorageService):
    """Simple local filesystem storage for development.

    Files are stored under the ``backend/media`` directory relative to the
    project root. The ``key`` is a path like ``avatars/<user_id>/<uuid>.<ext>``.
    ``get_url`` returns a relative URL that the FastAPI static files mount can
    serve (``/api/media/<key>``).
    """

    def __init__(self) -> None:
        # Resolve the media root relative to this file's location (project root)
        self.media_root = Path(__file__).resolve().parents[3] / "media"
        self.media_root.mkdir(parents=True, exist_ok=True)

    def upload(self, key: str, file: UploadFile) -> None:
        content, _ = read_image(file)
        dest_path = self.media_root / key
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(content)

    def delete(self, key: str) -> None:
        path = self.media_root / key
        path.unlink(missing_ok=True)

    def get_url(self, key: str) -> str:
        # Return a URL that FastAPI can serve via a static route (configured elsewhere)
        # For local backend the API serves ``/api/media/{key}``.
        return f"/api/media/{key}"
