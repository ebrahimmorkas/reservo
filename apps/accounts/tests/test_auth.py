import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "S3cure-pass!"


def test_register_creates_user_with_hashed_password(api_client):
    response = api_client.post(
        reverse("auth-register"),
        {"email": "Jane@Example.com", "password": PASSWORD, "role": "provider"},
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email="jane@example.com")
    assert user.role == User.Role.PROVIDER
    assert user.check_password(PASSWORD)
    assert "password" not in response.json()


def test_register_rejects_duplicate_email(api_client, customer):
    response = api_client.post(
        reverse("auth-register"),
        {"email": customer.email.upper(), "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.json()["error"]["details"]


def test_register_rejects_weak_password(api_client):
    response = api_client.post(
        reverse("auth-register"), {"email": "a@b.com", "password": "123"}, format="json"
    )

    assert response.status_code == 400


def test_obtain_token_and_access_profile(api_client, customer):
    token = api_client.post(
        reverse("auth-token"), {"email": customer.email, "password": PASSWORD}, format="json"
    )
    assert token.status_code == 200

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.json()['access']}")
    me = api_client.get(reverse("auth-me"))

    assert me.status_code == 200
    assert me.json()["email"] == customer.email


def test_profile_requires_authentication(api_client):
    assert api_client.get(reverse("auth-me")).status_code == 401


def test_user_cannot_change_own_role(customer_client, customer):
    response = customer_client.patch(reverse("auth-me"), {"role": "provider"}, format="json")

    assert response.status_code == 200
    customer.refresh_from_db()
    assert customer.role == User.Role.CUSTOMER


def test_logout_blacklists_refresh_token(api_client, customer):
    tokens = api_client.post(
        reverse("auth-token"), {"email": customer.email, "password": PASSWORD}, format="json"
    ).json()
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    assert (
        api_client.post(
            reverse("auth-logout"), {"refresh": tokens["refresh"]}, format="json"
        ).status_code
        == 205
    )
    refreshed = api_client.post(
        reverse("auth-token-refresh"), {"refresh": tokens["refresh"]}, format="json"
    )
    assert refreshed.status_code == 401
