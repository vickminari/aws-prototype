from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.file import (
    ACCEPTED_CONTENT_TYPES,
    FileDetail,
    FilePage,
    FileSummary,
    FileUpdate,
    StorageUsageRead,
    UploadInit,
    UploadTicket,
    media_type_for,
)


def test_upload_init_accepts_valid_file_and_strips_name():
    payload = UploadInit(filename="  praia.jpg ", size_bytes=2048, content_type="image/jpeg")

    assert payload.filename == "praia.jpg"


@pytest.mark.parametrize(
    "changes",
    [
        {"filename": ""},
        {"filename": "a" * 256},
        {"size_bytes": 0},
        {"content_type": "application/pdf"},
        {"content_type": "text/html"},
    ],
)
def test_upload_init_rejects_invalid_fields(changes):
    data = {"filename": "praia.jpg", "size_bytes": 2048, "content_type": "image/jpeg"} | changes

    with pytest.raises(ValidationError):
        UploadInit(**data)


@pytest.mark.parametrize(
    ("content_type", "media_type"),
    [("image/svg+xml", "image"), ("audio/flac", "audio"), ("video/x-msvideo", "video")],
)
def test_media_type_for_maps_content_type_to_media_type(content_type, media_type):
    assert media_type_for(content_type) == media_type


def test_accepted_content_types_cover_the_formats_of_the_specification():
    assert len(ACCEPTED_CONTENT_TYPES) == 13
    assert {media_type_for(content_type) for content_type in ACCEPTED_CONTENT_TYPES} == {
        "image",
        "audio",
        "video",
    }


def test_upload_ticket_serializes_post_form():
    ticket = UploadTicket(
        file_id=uuid4(), upload={"url": "https://s3/bucket", "fields": {"key": "k"}}, expires_in=900
    )

    assert ticket.model_dump(mode="json")["upload"] == {
        "url": "https://s3/bucket",
        "fields": {"key": "k"},
    }


def test_file_update_normalizes_tags_to_lowercase_without_repetition():
    update = FileUpdate(tags=[" Praia ", "praia", "FÉRIAS"])

    assert update.tags == ["praia", "férias"]


def test_file_update_rejects_11_tags():
    with pytest.raises(ValidationError):
        FileUpdate(tags=[f"tag{n}" for n in range(11)])


def test_file_update_accepts_10_tags_of_40_characters():
    tags = [f"{n}".ljust(40, "x") for n in range(10)]

    assert FileUpdate(tags=tags).tags == tags


@pytest.mark.parametrize("tag", ["a" * 41, "", "   "])
def test_file_update_rejects_invalid_tag(tag):
    with pytest.raises(ValidationError):
        FileUpdate(tags=[tag])


@pytest.mark.parametrize(
    "changes", [{"name": ""}, {"name": "a" * 256}, {"description": "a" * 2001}, {"genre": "a" * 51}]
)
def test_file_update_rejects_fields_above_limits(changes):
    with pytest.raises(ValidationError):
        FileUpdate(**changes)


def test_file_update_is_partial():
    assert FileUpdate().model_dump(exclude_unset=True) == {}


def _summary_data() -> dict:
    return {
        "id": uuid4(),
        "name": "clipe.mp4",
        "media_type": "video",
        "mime_type": "video/mp4",
        "size_bytes": 1024,
        "status": "ready",
        "thumbnail_url": None,
        "duration_seconds": 12.5,
        "tags": ["viagem"],
        "created_at": datetime(2026, 11, 27, tzinfo=UTC),
    }


def test_file_detail_extends_summary_with_type_metadata_and_variants():
    detail = FileDetail(
        **_summary_data(),
        original_filename="clipe.mp4",
        description=None,
        genre=None,
        error_code=None,
        updated_at=datetime(2026, 11, 27, tzinfo=UTC),
        processed_at=None,
        view_url="https://s3/view",
        download_url="https://s3/download",
        video={"duration_seconds": 12.5, "width": 1280, "height": 720},
        variants=[
            {
                "label": "720p",
                "width": 1280,
                "height": 720,
                "size_bytes": 1024,
                "url": "https://s3/720p",
                "is_original": True,
            }
        ],
        default_variant="720p",
    )

    data = detail.model_dump(mode="json")

    assert data["image"] is None
    assert data["video"]["width"] == 1280
    assert data["variants"][0]["label"] == "720p"
    assert data["default_variant"] == "720p"


def test_file_page_and_storage_usage():
    page = FilePage(items=[FileSummary(**_summary_data())], total=1, page=1, page_size=24)
    usage = StorageUsageRead(used_bytes=10, quota_bytes=100)

    assert page.items[0].media_type == "video"
    assert usage.model_dump() == {"used_bytes": 10, "quota_bytes": 100}
