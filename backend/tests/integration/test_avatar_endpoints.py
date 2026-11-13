from collections.abc import Iterator

import pytest
from fastapi import UploadFile

from app.dependencies import get_storage


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def upload(self, key: str, file: UploadFile) -> None:
        self.objects[key] = file.file.read()
        file.file.seek(0)

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)

    def get_url(self, key: str) -> str:
        return f"https://storage.example/{key}"


@pytest.fixture
def storage(app) -> Iterator[FakeStorage]:
    fake = FakeStorage()
    app.dependency_overrides[get_storage] = lambda: fake
    yield fake


PNG = b"\x89PNG\r\n\x1a\n" + b"valid image"


def test_upload_avatar_uses_signature_and_returns_url(client, auth_user, storage):
    response = client.post(
        "/api/users/me/avatar",
        files={"file": ("profile.txt", PNG, "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["profile_image_url"].startswith("https://storage.example/avatars/")
    assert list(storage.objects) == [auth_user.profile_image_key]
    assert auth_user.profile_image_key.endswith(".png")


@pytest.mark.parametrize(
    "content",
    [b"not an image", b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024)],
)
def test_upload_avatar_rejects_invalid_signature_or_size(client, auth_user, storage, content):
    response = client.post(
        "/api/users/me/avatar",
        files={"file": ("profile.png", content, "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_IMAGE"
    assert auth_user.profile_image_key is None
    assert storage.objects == {}


def test_second_upload_deletes_previous_and_delete_clears_image(client, auth_user, storage):
    first = client.post("/api/users/me/avatar", files={"file": ("one.png", PNG, "image/png")})
    first_key = "avatars/" + first.json()["profile_image_url"].split("/avatars/", 1)[1]
    second = client.post("/api/users/me/avatar", files={"file": ("two.png", PNG, "image/png")})

    assert second.status_code == 200
    assert first_key in storage.deleted
    assert auth_user.profile_image_key not in storage.deleted

    response = client.delete("/api/users/me/avatar")

    assert response.status_code == 200
    assert response.json()["profile_image_url"] is None
    assert auth_user.profile_image_key is None
