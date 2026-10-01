import logging
from datetime import timedelta
from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.bookings.models import Booking

from . import emails

logger = logging.getLogger(__name__)

RETRY_OPTIONS = {
    "autoretry_for": (SMTPException, ConnectionError),
    "retry_backoff": True,
    "retry_kwargs": {"max_retries": 5},
}

EVENTS = {
    "confirmed": emails.booking_confirmed,
    "cancelled": emails.booking_cancelled,
    "rescheduled": emails.booking_rescheduled,
}


def _load(booking_id: int) -> Booking | None:
    booking = (
        Booking.objects.select_related("service", "business__owner", "customer")
        .filter(pk=booking_id)
        .first()
    )
    if booking is None:
        logger.warning("Booking %s no longer exists; skipping notification", booking_id)
    return booking


@shared_task(**RETRY_OPTIONS)
def notify_booking_event(booking_id: int, event: str) -> None:
    booking = _load(booking_id)
    if booking is not None:
        EVENTS[event](booking)


@shared_task
def send_upcoming_reminders() -> int:
    """Email customers whose appointment starts within the reminder lead time.

    Each booking is "claimed" with a conditional UPDATE before sending, so running
    the task concurrently (or twice) never sends duplicate reminders.
    """
    now = timezone.now()
    window_end = now + timedelta(hours=settings.RESERVO_REMINDER_LEAD_HOURS)
    due = Booking.objects.active().filter(
        starts_at__gt=now, starts_at__lte=window_end, reminder_sent_at__isnull=True
    )

    sent = 0
    for booking_id in due.values_list("pk", flat=True):
        claimed = Booking.objects.filter(pk=booking_id, reminder_sent_at__isnull=True).update(
            reminder_sent_at=now
        )
        if claimed:
            send_reminder.delay(booking_id)
            sent += 1
    logger.info("Queued %d booking reminders", sent)
    return sent


@shared_task(**RETRY_OPTIONS)
def send_reminder(booking_id: int) -> None:
    booking = _load(booking_id)
    if booking is not None and booking.status == Booking.Status.CONFIRMED:
        emails.booking_reminder(booking)
