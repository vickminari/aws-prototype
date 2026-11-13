from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserRead, UserUpdate


@pytest.fixture
def registration_data():
    return {
        "full_name": "Maria Silva",
        "username": "maria.silva",
        "email": "maria@example.com",
        "password": "Senha123",
    }


def test_user_create_with_valid_data_accepts_optional_description(registration_data):
    user = UserCreate(**registration_data)

    assert user.full_name == registration_data["full_name"]
    assert user.username == registration_data["username"]
    assert user.email == registration_data["email"]
    assert user.description is None


@pytest.mark.parametrize("field", ["full_name", "username", "email", "password"])
def test_user_create_with_missing_required_field_raises_validation_error(field, registration_data):
    del registration_data[field]

    with pytest.raises(ValidationError) as error:
        UserCreate(**registration_data)

    assert field in {item["loc"][0] for item in error.value.errors()}


@pytest.mark.parametrize(
    "field, value",
    [
        ("full_name", ""),
        ("full_name", "   "),
        ("full_name", "a" * 121),
        ("username", "ab"),
        ("username", "a" * 31),
        ("username", "maria silva"),
        ("username", "maria-silva"),
        ("username", "maria@silva"),
        ("email", "nao-e-email"),
        ("email", "maria@"),
        ("email", "a" * 243 + "@example.com"),
        ("password", ""),
        ("password", "Senha12"),
        ("password", "abcdefgh"),
        ("password", "12345678"),
        ("description", "a" * 501),
    ],
)
def test_user_create_with_invalid_field_raises_validation_error(field, value, registration_data):
    registration_data[field] = value

    with pytest.raises(ValidationError) as error:
        UserCreate(**registration_data)

    assert field in {item["loc"][0] for item in error.value.errors()}


def test_user_create_accepts_maximum_documented_lengths(registration_data):
    registration_data.update(
        full_name="a" * 120,
        username="a" * 30,
        description="a" * 500,
    )

    user = UserCreate(**registration_data)

    assert len(user.full_name) == 120
    assert len(user.username) == 30
    assert len(user.description) == 500


@pytest.mark.parametrize("username", ["abc", "maria_silva", "maria.silva", "Maria.Silva"])
def test_user_create_accepts_valid_username(username, registration_data):
    # Maiúsculas precisam chegar à normalização antes de validar o formato final.
    registration_data["username"] = username

    UserCreate(**registration_data)


@pytest.mark.parametrize("description", [None, "", "Descrição do perfil"])
def test_user_create_accepts_optional_description_values(description, registration_data):
    user = UserCreate(**registration_data, description=description)

    assert user.description == description


@pytest.mark.parametrize("profile_image_url", [None, "https://example.com/avatar.png"])
def test_user_read_from_attributes_serializes_only_public_fields(profile_image_url):
    user_id = UUID("12345678-1234-4234-8234-123456789abc")
    created_at = datetime(2026, 11, 7, 12, tzinfo=UTC)
    user = SimpleNamespace(
        id=user_id,
        full_name="Maria Silva",
        username="maria.silva",
        email="maria@example.com",
        description=None,
        profile_image_url=profile_image_url,
        created_at=created_at,
        password="Senha123",
        hashed_password="hash-que-nao-pode-ser-retornado",
        profile_image_key="avatars/privado.png",
        is_active=True,
    )

    result = UserRead.model_validate(user)
    serialized = result.model_dump(mode="json")

    assert result.id == user_id
    assert result.created_at == created_at
    assert serialized == {
        "id": str(user_id),
        "full_name": "Maria Silva",
        "username": "maria.silva",
        "email": "maria@example.com",
        "description": None,
        "profile_image_url": profile_image_url,
        "created_at": "2026-11-07T12:00:00Z",
    }
    assert user.password not in result.model_dump_json()
    assert user.hashed_password not in result.model_dump_json()


@pytest.mark.parametrize(
    "username", ["maria@example.com", "maria silva", "ma", "a" * 31, "maria-silva", None]
)
def test_user_update_rejects_username_outside_registration_rules(username):
    with pytest.raises(ValidationError) as error:
        UserUpdate(username=username)

    assert error.value.errors()[0]["loc"] == ("username",)


@pytest.mark.parametrize("email", ["sem-arroba", "dona", "a@" + "b" * 250 + ".com", None])
def test_user_update_rejects_invalid_email(email):
    with pytest.raises(ValidationError) as error:
        UserUpdate(email=email)

    assert error.value.errors()[0]["loc"] == ("email",)


def test_user_update_accepts_partial_valid_identity():
    update = UserUpdate(username="Maria.Silva_2", email="maria@example.com")

    assert update.model_dump(exclude_unset=True) == {
        "username": "Maria.Silva_2",
        "email": "maria@example.com",
    }
    assert UserUpdate().model_dump(exclude_unset=True) == {}
