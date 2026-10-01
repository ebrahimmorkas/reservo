from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.tests.factories import BookingFactory
from apps.bookings.tests.test_bookings_api import book, future_slot
from apps.catalog.tests.factories import BusinessFactory, ServiceFactory
from apps.notifications.tasks import notify_booking_event, send_upcoming_reminders
from apps.scheduling.tests.factories import open_every_day

pytestmark = pytest.mark.django_db


@pytest.fixture
def service(provider_user):
    business = BusinessFactory(owner=provider_user, timezone="Europe/Berlin")
    open_every_day(business)
    return ServiceFactory(business=business, name="Deep Tissue Massage", duration_minutes=60)


def test_booking_sends_confirmation_to_customer_and_provider(
    customer_client, customer, provider_user, service, django_capture_on_commit_callbacks
):
    slot = future_slot(hour=9)
    with django_capture_on_commit_callbacks(execute=True):
        response = book(customer_client, service, slot)
    assert response.status_code == 201

    recipients = {m.to[0]: m for m in mail.outbox}
    assert set(recipients) == {customer.email, provider_user.email}
    confirmation = recipients[customer.email]
    assert confirmation.subject == "Booking confirmed: Deep Tissue Massage"
    local = slot.astimezone(ZoneInfo("Europe/Berlin"))
    assert f"at {local:%H:%M} (Europe/Berlin)" in confirmation.body
    assert "(Europe/Berlin)" in confirmation.body


def test_no_email_when_transaction_rolls_back(customer_client, service):
    # Without executing on-commit callbacks nothing is sent: emails never leak
    # for bookings that were not persisted.
    book(customer_client, service, future_slot())

    assert mail.outbox == []


def test_cancellation_notifies_both_parties(
    customer_client, customer, service, django_capture_on_commit_callbacks
):
    booking = BookingFactory(customer=customer, service=service)

    with django_capture_on_commit_callbacks(execute=True):
        customer_client.post(
            reverse("booking-cancel", args=[booking.pk]), {"reason": "Travel"}, format="json"
        )

    assert len(mail.outbox) == 2
    assert all("Travel" in m.body for m in mail.outbox)


def test_notification_for_deleted_booking_is_skipped():
    notify_booking_event(999_999, "confirmed")

    assert mail.outbox == []


def test_reminders_sent_once_for_bookings_inside_lead_time(service):
    soon = BookingFactory(service=service, starts_at=timezone.now() + timedelta(hours=3))
    BookingFactory(service=service, starts_at=timezone.now() + timedelta(days=5))
    BookingFactory(
        service=service,
        starts_at=timezone.now() + timedelta(hours=4),
        status=Booking.Status.CANCELLED,
    )

    assert send_upcoming_reminders() == 1
    assert send_upcoming_reminders() == 0  # idempotent

    assert [m.to for m in mail.outbox] == [[soon.customer.email]]
    soon.refresh_from_db()
    assert soon.reminder_sent_at is not None


def test_send_reminders_management_command(service, capsys):
    BookingFactory(service=service, starts_at=timezone.now() + timedelta(hours=1))

    call_command("send_reminders")

    assert "Queued 1 reminder(s)." in capsys.readouterr().out
