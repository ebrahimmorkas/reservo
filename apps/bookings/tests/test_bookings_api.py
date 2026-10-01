from datetime import UTC, datetime, time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.bookings.models import Booking
from apps.bookings.tests.factories import BookingFactory
from apps.catalog.tests.factories import BusinessFactory, ServiceFactory
from apps.scheduling.tests.factories import open_every_day

pytestmark = pytest.mark.django_db


def future_slot(days: int = 3, hour: int = 10, minute: int = 0) -> datetime:
    day = timezone.localdate() + timedelta(days=days)
    return datetime.combine(day, time(hour, minute), tzinfo=UTC)


@pytest.fixture
def service(provider_user):
    business = BusinessFactory(owner=provider_user)
    open_every_day(business)
    return ServiceFactory(business=business, duration_minutes=60, buffer_minutes=15)


def book(client, service, starts_at, **extra):
    return client.post(
        reverse("booking-list"),
        {"service": service.pk, "starts_at": starts_at.isoformat(), **extra},
        format="json",
    )


def test_customer_books_available_slot(customer_client, customer, service):
    response = book(customer_client, service, future_slot(), notes="First visit")

    assert response.status_code == 201, response.json()
    booking = Booking.objects.get()
    assert booking.customer == customer
    assert booking.ends_at - booking.starts_at == timedelta(minutes=60)
    assert booking.blocked_until - booking.ends_at == timedelta(minutes=15)
    assert booking.price == service.price


def test_cannot_double_book_a_slot(customer_client, service):
    assert book(customer_client, service, future_slot()).status_code == 201

    response = book(customer_client, service, future_slot())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "slot_unavailable"


def test_buffer_blocks_the_following_slot(customer_client, service):
    book(customer_client, service, future_slot(hour=10))

    # 10:00-11:00 + 15 min buffer -> 11:00 is blocked, 11:15 is free
    assert book(customer_client, service, future_slot(hour=11)).status_code == 409
    assert book(customer_client, service, future_slot(hour=11, minute=15)).status_code == 201


def test_cannot_book_outside_working_hours(customer_client, service):
    assert book(customer_client, service, future_slot(hour=20)).status_code == 409


def test_cannot_book_in_the_past(customer_client, service):
    assert book(customer_client, service, future_slot(days=-1)).status_code == 409


def test_booking_removes_slot_from_availability(
    customer_client, api_client, service, django_capture_on_commit_callbacks
):
    slot = future_slot()
    url = reverse("service-availability", args=[service.pk])
    assert (
        slot.isoformat().replace("+00:00", "Z")
        in api_client.get(url, {"date": slot.date().isoformat()}).json()["slots"]
    )

    with django_capture_on_commit_callbacks(execute=True):
        book(customer_client, service, slot)

    slots = api_client.get(url, {"date": slot.date().isoformat()}).json()["slots"]
    assert slot.isoformat().replace("+00:00", "Z") not in slots


def test_users_only_see_their_own_bookings(customer_client, customer, service):
    mine = BookingFactory(customer=customer, service=service)
    BookingFactory()

    response = customer_client.get(reverse("booking-list"))

    assert [b["id"] for b in response.json()["results"]] == [mine.pk]


def test_provider_sees_bookings_for_their_business(provider_client, service):
    booking = BookingFactory(service=service)

    response = provider_client.get(reverse("booking-list"), {"role": "provider"})

    assert [b["id"] for b in response.json()["results"]] == [booking.pk]


def test_customer_cancels_booking(customer_client, customer, service):
    booking = BookingFactory(customer=customer, service=service)

    response = customer_client.post(
        reverse("booking-cancel", args=[booking.pk]), {"reason": "Sick"}, format="json"
    )

    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CANCELLED
    assert booking.cancellation_reason == "Sick"


def test_customer_cannot_cancel_inside_cancellation_window(customer_client, customer, service):
    booking = BookingFactory(
        customer=customer, service=service, starts_at=timezone.now() + timedelta(minutes=30)
    )

    response = customer_client.post(reverse("booking-cancel", args=[booking.pk]))

    assert response.status_code == 409


def test_provider_can_cancel_anytime(provider_client, service):
    booking = BookingFactory(service=service, starts_at=timezone.now() + timedelta(minutes=30))

    assert provider_client.post(reverse("booking-cancel", args=[booking.pk])).status_code == 200


def test_cancelled_slot_becomes_bookable_again(customer_client, customer, service):
    slot = future_slot()
    booking_id = book(customer_client, service, slot).json()["id"]
    customer_client.post(reverse("booking-cancel", args=[booking_id]))

    assert book(customer_client, service, slot).status_code == 201


def test_reschedule_moves_booking(customer_client, service):
    booking_id = book(customer_client, service, future_slot(hour=10)).json()["id"]

    response = customer_client.post(
        reverse("booking-reschedule", args=[booking_id]),
        {"starts_at": future_slot(hour=10, minute=30).isoformat()},  # overlaps its own slot
        format="json",
    )

    assert response.status_code == 200
    assert Booking.objects.get().starts_at == future_slot(hour=10, minute=30)


def test_reschedule_into_taken_slot_fails(customer_client, service):
    BookingFactory(service=service, starts_at=future_slot(hour=14))
    booking_id = book(customer_client, service, future_slot(hour=10)).json()["id"]

    response = customer_client.post(
        reverse("booking-reschedule", args=[booking_id]),
        {"starts_at": future_slot(hour=14).isoformat()},
        format="json",
    )

    assert response.status_code == 409


def test_only_owner_records_outcome(customer_client, provider_client, customer, service):
    booking = BookingFactory(
        customer=customer, service=service, starts_at=timezone.now() - timedelta(hours=2)
    )

    assert customer_client.post(reverse("booking-complete", args=[booking.pk])).status_code == 403
    assert provider_client.post(reverse("booking-no-show", args=[booking.pk])).status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.NO_SHOW


def test_outcome_cannot_be_recorded_for_future_booking(provider_client, service):
    booking = BookingFactory(service=service)

    assert provider_client.post(reverse("booking-complete", args=[booking.pk])).status_code == 409


def test_strangers_cannot_see_booking(service):
    from rest_framework.test import APIClient

    booking = BookingFactory(service=service)
    client = APIClient()
    client.force_authenticate(UserFactory())

    assert client.get(reverse("booking-detail", args=[booking.pk])).status_code == 404
