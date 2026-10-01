import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def customer(db):
    return UserFactory(role="customer")


@pytest.fixture
def provider_user(db):
    return UserFactory(role="provider")


@pytest.fixture
def customer_client(customer) -> APIClient:
    client = APIClient()
    client.force_authenticate(customer)
    return client


@pytest.fixture
def provider_client(provider_user) -> APIClient:
    client = APIClient()
    client.force_authenticate(provider_user)
    return client
