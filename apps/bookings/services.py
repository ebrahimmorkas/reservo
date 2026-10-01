"""Booking business logic.

Double booking is prevented by serialising writes per business: the business row
is locked with ``SELECT ... FOR UPDATE`` and the slot is re-validated against the
database (never the cache) while the lock is held. Two concurrent requests for the
same slot therefore cannot both succeed.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Business, Service
from apps.core.exceptions import DomainError
from apps.scheduling.availability import compute_slots

from .models import Booking


class SlotUnavailable(DomainError):
    default_code = "slot_unavailable"
    default_detail = "The requested time slot is no longer available."


class InvalidTransition(DomainError):
    default_code = "invalid_transition"
    default_detail = "This action is not allowed for the booking in its current state."


def _assert_bookable(service: Service, starts_at: datetime, *, exclude: Booking | None = None):
    earliest = timezone.now() + timedelta(minutes=settings.RESERVO_MIN_NOTICE_MINUTES)
    horizon = timezone.now() + timedelta(days=settings.RESERVO_BOOKING_HORIZON_DAYS)
    if not earliest <= starts_at <= horizon:
        raise SlotUnavailable("The requested time is outside the bookable window.")

    local_day = starts_at.astimezone(ZoneInfo(service.business.timezone)).date()
    if starts_at not in compute_slots(service, local_day, exclude_booking=exclude):
        raise SlotUnavailable()


def _lock_business(business_id: int) -> Business:
    return Business.objects.select_for_update().get(pk=business_id)


@transaction.atomic
def create_booking(*, customer, service: Service, starts_at: datetime, notes: str = "") -> Booking:
    if not (service.is_active and service.business.is_active):
        raise SlotUnavailable("This service is not currently bookable.")

    _lock_business(service.business_id)
    _assert_bookable(service, starts_at)

    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    return Booking.objects.create(
        customer=customer,
        business_id=service.business_id,
        service=service,
        starts_at=starts_at,
        ends_at=ends_at,
        blocked_until=ends_at + timedelta(minutes=service.buffer_minutes),
        price=service.price,
        notes=notes,
    )


@transaction.atomic
def reschedule_booking(*, booking: Booking, starts_at: datetime, actor) -> Booking:
    _require_status(booking, Booking.Status.CONFIRMED)
    if booking.customer_id == actor.pk and booking.business.owner_id != actor.pk:
        _require_customer_change_window(booking)

    _lock_business(booking.business_id)
    service = booking.service
    _assert_bookable(service, starts_at, exclude=booking)

    booking.starts_at = starts_at
    booking.ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    booking.blocked_until = booking.ends_at + timedelta(minutes=service.buffer_minutes)
    booking.reminder_sent_at = None
    booking.save(
        update_fields=["starts_at", "ends_at", "blocked_until", "reminder_sent_at", "updated_at"]
    )
    return booking


@transaction.atomic
def cancel_booking(*, booking: Booking, actor, reason: str = "") -> Booking:
    _require_status(booking, Booking.Status.CONFIRMED)
    is_owner = booking.business.owner_id == actor.pk
    if not is_owner:
        _require_customer_change_window(booking)

    booking.status = Booking.Status.CANCELLED
    booking.cancelled_at = timezone.now()
    booking.cancellation_reason = reason
    booking.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
    return booking


@transaction.atomic
def mark_outcome(*, booking: Booking, status: str) -> Booking:
    """Provider marks a past appointment as completed or no-show."""
    _require_status(booking, Booking.Status.CONFIRMED)
    if booking.starts_at > timezone.now():
        raise InvalidTransition("Outcomes can only be recorded after the appointment started.")
    booking.status = status
    booking.save(update_fields=["status", "updated_at"])
    return booking


def _require_status(booking: Booking, status: str) -> None:
    if booking.status != status:
        raise InvalidTransition()


def _require_customer_change_window(booking: Booking) -> None:
    deadline = booking.starts_at - timedelta(hours=settings.RESERVO_CANCELLATION_WINDOW_HOURS)
    if timezone.now() > deadline:
        raise InvalidTransition(
            f"Bookings can only be changed up to "
            f"{settings.RESERVO_CANCELLATION_WINDOW_HOURS} hours before the start time."
        )
