from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.catalog.tests.factories import BusinessFactory, ServiceFactory
from apps.scheduling.models import WorkingHours
from apps.scheduling.tests.factories import WorkingHoursFactory, open_every_day

pytestmark = pytest.mark.django_db


def test_provider_creates_working_hours(provider_client, provider_user):
    business = BusinessFactory(owner=provider_user)

    response = provider_client.post(
        reverse("working-hours-list"),
        {"business": business.slug, "weekday": 0, "start_time": "09:00", "end_time": "17:00"},
        format="json",
    )

    assert response.status_code == 201
    assert WorkingHours.objects.filter(business=business).count() == 1


def test_working_hours_must_not_overlap(provider_client, provider_user):
    business = BusinessFactory(owner=provider_user)
    WorkingHoursFactory(business=business, weekday=0)

    response = provider_client.post(
        reverse("working-hours-list"),
        {"business": business.slug, "weekday": 0, "start_time": "16:00", "end_time": "18:00"},
        format="json",
    )

    assert response.status_code == 400


def test_working_hours_end_must_follow_start(provider_client, provider_user):
    business = BusinessFactory(owner=provider_user)

    response = provider_client.post(
        reverse("working-hours-list"),
        {"business": business.slug, "weekday": 0, "start_time": "17:00", "end_time": "09:00"},
        format="json",
    )

    assert response.status_code == 400


def test_provider_cannot_manage_foreign_business_hours(provider_client):
    other = BusinessFactory()
    hours = WorkingHoursFactory(business=other)

    create = provider_client.post(
        reverse("working-hours-list"),
        {"business": other.slug, "weekday": 1, "start_time": "09:00", "end_time": "17:00"},
        format="json",
    )
    delete = provider_client.delete(reverse("working-hours-detail", args=[hours.pk]))

    assert create.status_code == 400
    assert delete.status_code == 404


def test_customer_cannot_access_time_off(customer_client):
    assert customer_client.get(reverse("time-off-list")).status_code == 403


def test_public_availability_endpoint(api_client):
    service = ServiceFactory(duration_minutes=60)
    open_every_day(service.business)
    day = timezone.localdate() + timedelta(days=3)

    response = api_client.get(
        reverse("service-availability", args=[service.pk]), {"date": day.isoformat()}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "UTC"
    assert len(body["slots"]) == 29  # 09:00 .. 16:00 every 15 minutes


def test_availability_rejects_dates_beyond_horizon(api_client, settings):
    settings.RESERVO_BOOKING_HORIZON_DAYS = 30
    service = ServiceFactory()
    day = timezone.localdate() + timedelta(days=31)

    response = api_client.get(
        reverse("service-availability", args=[service.pk]), {"date": day.isoformat()}
    )

    assert response.status_code == 400
