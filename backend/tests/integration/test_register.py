from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.core.security import verify_password
from app.models import User

REGISTER_URL = "/api/auth/register"


@pytest.fixture
def registration_data():
    return {
        "full_name": "Maria Silva",
        "username": "Maria.Silva",
        "email": "Maria.Silva@EXAMPLE.COM",
        "password": "Senha123",
    }


@pytest.mark.parametrize("description", [None, "Descrição do perfil"])
def test_register_returns_201_with_public_user_and_persists_hash(
    csrf_client, db_session, registration_data, description
):
    response = csrf_client.post(REGISTER_URL, json=registration_data | {"description": description})

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "id",
        "full_name",
        "username",
        "email",
        "description",
        "profile_image_url",
        "created_at",
    }
    assert body["full_name"] == "Maria Silva"
    assert body["username"] == "maria.silva"
    assert body["email"] == "maria.silva@example.com"
    assert body["description"] == description
    assert body["profile_image_url"] is None
    assert datetime.fromisoformat(body["created_at"]).utcoffset() is not None
    saved = db_session.get(User, UUID(body["id"]))
    assert saved is not None
    assert verify_password(registration_data["password"], saved.hashed_password)
    assert registration_data["password"] not in response.text
    assert saved.hashed_password not in response.text
    # Cadastro não realiza login automático no backend: esse fluxo pertence à #9.
    assert "set-cookie" not in response.headers


def test_register_without_description_returns_null(csrf_client, registration_data):
    response = csrf_client.post(REGISTER_URL, json=registration_data)

    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.parametrize(
    "field, value, expected_body",
    [
        (
            "email",
            "maria@example.com",
            {"detail": "Email já cadastrado", "code": "EMAIL_ALREADY_EXISTS"},
        ),
        (
            "email",
            "MARIA@EXAMPLE.COM",
            {"detail": "Email já cadastrado", "code": "EMAIL_ALREADY_EXISTS"},
        ),
        (
            "username",
            "maria.silva",
            {"detail": "Nome de usuário já cadastrado", "code": "USERNAME_ALREADY_EXISTS"},
        ),
        (
            "username",
            "MARIA.SILVA",
            {"detail": "Nome de usuário já cadastrado", "code": "USERNAME_ALREADY_EXISTS"},
        ),
    ],
)
def test_register_with_duplicate_identity_returns_409(
    csrf_client, db_session, user_factory, registration_data, field, value, expected_body
):
    user_factory(username="maria.silva", email="maria@example.com")

    response = csrf_client.post(REGISTER_URL, json=registration_data | {field: value})

    assert response.status_code == 409
    assert response.json() == expected_body
    assert db_session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize(
    "field, value",
    [
        ("full_name", ""),
        ("full_name", "a" * 121),
        ("username", "ab"),
        ("username", "maria silva"),
        ("username", "a" * 31),
        ("email", "email-invalido"),
        ("password", "Abc123"),
        ("password", "abcdefgh"),
        ("password", "12345678"),
        ("description", "a" * 501),
    ],
)
def test_register_with_invalid_field_returns_422_without_persisting(
    csrf_client, db_session, registration_data, field, value
):
    response = csrf_client.post(REGISTER_URL, json=registration_data | {field: value})

    assert response.status_code == 422
    assert "password" not in registration_data or registration_data["password"] not in response.text
    assert db_session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("field", ["full_name", "username", "email", "password"])
def test_register_with_missing_required_field_returns_422(csrf_client, registration_data, field):
    del registration_data[field]

    response = csrf_client.post(REGISTER_URL, json=registration_data)

    assert response.status_code == 422
    if "password" in registration_data:
        assert registration_data["password"] not in response.text


def test_register_validation_error_does_not_echo_password(csrf_client, registration_data):
    password = "senhaSecretaSemNumeros"

    response = csrf_client.post(REGISTER_URL, json=registration_data | {"password": password})

    assert response.status_code == 422
    assert password not in response.text
    errors = response.json()["detail"]
    assert any(error["loc"] == ["body", "password"] for error in errors)
    assert all(set(error) == {"loc", "msg", "type"} for error in errors)


def test_register_is_documented_as_public_with_expected_responses(csrf_client):
    response = csrf_client.get("/api/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"][REGISTER_URL]["post"]
    assert not operation.get("security")
    assert {"201", "409", "422"} <= set(operation["responses"])
    assert operation["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/UserRead"
    }
    assert operation["responses"]["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ValidationErrorRead"
    }
    examples = operation["responses"]["409"]["content"]["application/json"]["examples"]
    assert examples["email"]["value"]["code"] == "EMAIL_ALREADY_EXISTS"
    assert examples["username"]["value"]["code"] == "USERNAME_ALREADY_EXISTS"


def test_register_with_invalid_json_returns_422_without_echoing_body(csrf_client):
    password = "Senha-secreta-123"

    response = csrf_client.post(
        REGISTER_URL,
        content='{"password": "' + password + '",',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert password not in response.text
    assert all(set(error) == {"loc", "msg", "type"} for error in response.json()["detail"])
