"""Testes de perfil e troca de senha do usuário autenticado."""

from datetime import datetime

import pytest

from app.core.security import verify_password

DEFAULT_PASSWORD = "Senha-de-teste-123"


def test_get_me_returns_user_data_and_created_at(csrf_client, auth_user):
    response = csrf_client.get("/api/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(auth_user.id)
    assert data["full_name"] == auth_user.full_name
    assert data["username"] == auth_user.username
    assert data["email"] == auth_user.email
    assert data["profile_image_url"] is None
    assert data["description"] == auth_user.description
    assert data["is_active"] is auth_user.is_active
    assert datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) == auth_user.created_at


def test_patch_me_updates_only_sent_fields(csrf_client, auth_user):
    original = {
        "username": auth_user.username,
        "email": auth_user.email,
        "description": auth_user.description,
    }

    response = csrf_client.patch("/api/users/me", json={"full_name": "Nome atualizado"})

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Nome atualizado"
    assert data["username"] == original["username"]
    assert data["email"] == original["email"]
    assert data["description"] == original["description"]


def test_patch_me_rejects_email_used_by_another_user(csrf_client, auth_user, user_factory):
    other_user = user_factory()

    response = csrf_client.patch("/api/users/me", json={"email": other_user.email})

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_ALREADY_EXISTS"


def test_patch_me_allows_own_email(csrf_client, auth_user):
    response = csrf_client.patch("/api/users/me", json={"email": auth_user.email})

    assert response.status_code == 200
    assert response.json()["email"] == auth_user.email


def test_patch_me_does_not_change_created_at(csrf_client, auth_user):
    original_created_at = auth_user.created_at

    response = csrf_client.patch(
        "/api/users/me",
        json={"created_at": datetime(2000, 1, 1).isoformat()},
    )

    assert response.status_code == 200
    assert (
        datetime.fromisoformat(response.json()["created_at"].replace("Z", "+00:00"))
        == original_created_at
    )


def test_change_password_rejects_wrong_current_password(csrf_client, auth_user):
    response = csrf_client.put(
        "/api/users/me/password",
        json={
            "current_password": "senha-incorreta",
            "new_password": "NovaSenha-de-teste-456!",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "WRONG_PASSWORD"


@pytest.mark.parametrize(
    "new_password",
    ["curta", DEFAULT_PASSWORD],
)
def test_change_password_rejects_weak_or_repeated_password(csrf_client, auth_user, new_password):
    response = csrf_client.put(
        "/api/users/me/password",
        json={
            "current_password": DEFAULT_PASSWORD,
            "new_password": new_password,
        },
    )

    assert response.status_code == 422


def test_change_password_updates_hash_and_returns_no_content(csrf_client, auth_user):
    new_password = "NovaSenha-de-teste-456!"

    response = csrf_client.put(
        "/api/users/me/password",
        json={
            "current_password": DEFAULT_PASSWORD,
            "new_password": new_password,
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    assert verify_password(new_password, auth_user.hashed_password)


@pytest.mark.parametrize(
    "payload",
    [{"username": "vitima@example.com"}, {"email": "vitima"}, {"username": None}],
)
def test_patch_me_rejects_identity_that_could_collide_on_login(
    csrf_client, auth_user, db_session, payload
):
    original = (auth_user.username, auth_user.email)

    response = csrf_client.patch("/api/users/me", json=payload)

    assert response.status_code == 422
    db_session.refresh(auth_user)
    assert (auth_user.username, auth_user.email) == original
