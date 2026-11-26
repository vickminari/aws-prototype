from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import (
    AudioMetadata,
    ImageMetadata,
    MediaObject,
    MediaVariant,
    Tag,
    VideoMetadata,
    media_tags,
)


def test_create_media_with_metadata_and_tags_persists_and_reads(
    db_session, user_factory, media_factory
):
    owner = user_factory()
    media = media_factory(owner, persist=False)
    media.image = ImageMetadata(width=800, height=600, format="JPEG", exif={"Make": "Canon"})
    media.tags = [Tag(owner_id=owner.id, name="praia"), Tag(owner_id=owner.id, name="férias")]
    db_session.add(media)
    db_session.commit()
    db_session.expunge_all()

    saved = db_session.get(MediaObject, media.id)

    assert isinstance(saved.id, UUID)
    assert saved.status == "pending_upload"
    assert saved.attempts == 0
    assert isinstance(saved.created_at, datetime)
    assert saved.processed_at is None
    assert saved.image.width == 800
    assert saved.image.exif == {"Make": "Canon"}
    assert saved.video is None
    assert sorted(tag.name for tag in saved.tags) == ["férias", "praia"]


def test_create_video_with_metadata_and_variants(db_session, user_factory, media_factory):
    owner = user_factory()
    media = media_factory(
        owner, persist=False, media_type="video", extension="mp4", mime_type="video/mp4"
    )
    media.video = VideoMetadata(duration_seconds=12.5, width=1920, height=1080, fps=30.0)
    media.variants = [
        MediaVariant(
            label="1080p",
            width=1920,
            height=1080,
            size_bytes=2048,
            storage_key=media.storage_key,
            is_original=True,
        ),
        MediaVariant(
            label="720p",
            width=1280,
            height=720,
            size_bytes=1024,
            storage_key=f"users/{owner.id}/videos/{media.id}/720p.mp4",
        ),
    ]
    db_session.add(media)
    db_session.commit()
    db_session.expunge_all()

    saved = db_session.get(MediaObject, media.id)

    assert saved.video.duration_seconds == 12.5
    assert {variant.label: variant.is_original for variant in saved.variants} == {
        "1080p": True,
        "720p": False,
    }


def test_create_audio_with_metadata(db_session, user_factory, media_factory):
    owner = user_factory()
    media = media_factory(
        owner, persist=False, media_type="audio", extension="mp3", mime_type="audio/mpeg"
    )
    media.audio = AudioMetadata(
        duration_seconds=180.0, bitrate=128000, sample_rate=44100, channels=2, codec="mp3"
    )
    db_session.add(media)
    db_session.commit()
    db_session.expunge_all()

    assert db_session.get(MediaObject, media.id).audio.channels == 2


def test_new_user_starts_with_zero_storage_used(user_factory):
    assert user_factory().storage_used_bytes == 0


def test_repeated_tag_for_same_owner_raises_integrity_error(db_session, user_factory):
    owner = user_factory()
    db_session.add(Tag(owner_id=owner.id, name="praia"))
    db_session.commit()

    db_session.add(Tag(owner_id=owner.id, name="praia"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_tag_name_for_different_owners_is_allowed(db_session, user_factory):
    first, second = user_factory(), user_factory()
    db_session.add_all(
        [Tag(owner_id=first.id, name="praia"), Tag(owner_id=second.id, name="praia")]
    )

    db_session.commit()


def test_repeated_variant_label_for_same_media_raises_integrity_error(
    db_session, user_factory, media_factory
):
    media = media_factory(user_factory(), persist=False, media_type="video")
    db_session.add(media)
    db_session.commit()

    for key in ("a.mp4", "b.mp4"):
        db_session.add(
            MediaVariant(
                media_id=media.id,
                label="720p",
                width=1280,
                height=720,
                size_bytes=1,
                storage_key=key,
            )
        )
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize(("field", "value"), [("media_type", "document"), ("status", "deleted")])
def test_invalid_media_type_or_status_raises_integrity_error(
    field, value, db_session, user_factory, media_factory
):
    db_session.add(media_factory(user_factory(), persist=False, **{field: value}))

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_storage_key_raises_integrity_error(db_session, user_factory, media_factory):
    owner = user_factory()
    db_session.add(media_factory(owner, persist=False, storage_key="users/x/images/y/original.jpg"))
    db_session.commit()

    db_session.add(media_factory(owner, persist=False, storage_key="users/x/images/y/original.jpg"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_media_with_unknown_owner_raises_integrity_error(db_session, user_factory, media_factory):
    owner = user_factory()
    db_session.add(media_factory(owner, persist=False, owner_id=uuid4()))

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_media_removes_metadata_variants_and_tag_links(
    db_session, user_factory, media_factory
):
    owner = user_factory()
    media = media_factory(
        owner, persist=False, media_type="video", extension="mp4", mime_type="video/mp4"
    )
    media.video = VideoMetadata(duration_seconds=1.0, width=640, height=360)
    media.variants = [
        MediaVariant(
            label="360p",
            width=640,
            height=360,
            size_bytes=1,
            storage_key=media.storage_key,
            is_original=True,
        )
    ]
    media.tags = [Tag(owner_id=owner.id, name="viagem")]
    db_session.add(media)
    db_session.commit()

    db_session.delete(media)
    db_session.commit()

    def count(statement):
        return db_session.scalar(select(func.count()).select_from(statement))

    assert count(VideoMetadata) == 0
    assert count(MediaVariant) == 0
    assert count(media_tags) == 0
    # A tag continua no vocabulário do usuário; só a associação com o arquivo some
    assert count(Tag) == 1


def test_media_factory_persists_file_with_new_owner_by_default(db_session, media_factory):
    media = media_factory()
    db_session.expunge_all()

    saved = db_session.get(MediaObject, media.id)

    assert saved.storage_key == f"users/{saved.owner_id}/images/{saved.id}/original.jpg"
