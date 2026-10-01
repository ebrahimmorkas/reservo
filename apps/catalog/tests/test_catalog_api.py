import pytest
from django.urls import reverse

from apps.catalog.models import Business
from apps.catalog.tests.factories import BusinessFactory, ServiceFactory

pytestmark = pytest.mark.django_db


def test_provider_can_create_business_with_generated_slug(provider_client, provider_user):
    response = provider_client.post(
        reverse("business-list"),
        {"name": "Fade Masters", "timezone": "Europe/London"},
        format="json",
    )

    assert response.status_code == 201
    business = Business.objects.get()
    assert business.slug == "fade-masters"
    assert business.owner == provider_user


def test_duplicate_business_names_get_unique_slugs(provider_user):
    first = BusinessFactory(name="Glow", owner=provider_user)
    second = BusinessFactory(name="Glow", owner=provider_user)

    assert (first.slug, second.slug) == ("glow", "glow-2")


def test_customer_cannot_create_business(customer_client):
    response = customer_client.post(reverse("business-list"), {"name": "Nope"}, format="json")

    assert response.status_code == 403


def test_invalid_timezone_is_rejected(provider_client):
    response = provider_client.post(
        reverse("business-list"), {"name": "X", "timezone": "Mars/Base"}, format="json"
    )

    assert response.status_code == 400


def test_anonymous_users_only_see_active_businesses(api_client):
    BusinessFactory(name="Open")
    BusinessFactory(name="Closed", is_active=False)

    response = api_client.get(reverse("business-list"))

    assert [b["name"] for b in response.json()["results"]] == ["Open"]


def test_owner_sees_own_inactive_business(provider_client, provider_user):
    BusinessFactory(name="Hidden", owner=provider_user, is_active=False)

    response = provider_client.get(reverse("business-list"))

    assert [b["name"] for b in response.json()["results"]] == ["Hidden"]


def test_only_owner_can_update_business(provider_client, provider_user):
    mine = BusinessFactory(owner=provider_user)
    theirs = BusinessFactory()

    ok = provider_client.patch(
        reverse("business-detail", args=[mine.slug]), {"phone": "123"}, format="json"
    )
    forbidden = provider_client.patch(
        reverse("business-detail", args=[theirs.slug]), {"phone": "123"}, format="json"
    )

    assert ok.status_code == 200
    assert forbidden.status_code == 403


def test_provider_can_add_service_to_own_business(provider_client, provider_user):
    business = BusinessFactory(owner=provider_user)

    response = provider_client.post(
        reverse("service-list"),
        {"business": business.slug, "name": "Cut", "duration_minutes": 45, "price": "30.00"},
        format="json",
    )

    assert response.status_code == 201
    assert business.services.get().duration_minutes == 45


def test_provider_cannot_add_service_to_foreign_business(provider_client):
    other = BusinessFactory()

    response = provider_client.post(
        reverse("service-list"),
        {"business": other.slug, "name": "Cut", "duration_minutes": 45, "price": "30.00"},
        format="json",
    )

    assert response.status_code == 400
    assert "business" in response.json()["error"]["details"]


def test_services_can_be_filtered_by_business_and_price(api_client):
    cheap = ServiceFactory(price="10.00")
    ServiceFactory(price="99.00", business=cheap.business)
    ServiceFactory(price="10.00")

    response = api_client.get(
        reverse("service-list"), {"business": cheap.business.slug, "max_price": 50}
    )

    assert [s["id"] for s in response.json()["results"]] == [cheap.id]
