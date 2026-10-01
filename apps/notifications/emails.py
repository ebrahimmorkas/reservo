"""Plain-text transactional emails rendered from templates."""

from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.bookings.models import Booking


def _send(template: str, subject: str, booking: Booking, recipient: str) -> None:
    # Templates localise datetimes to the *active* time zone, so render in the
    # business' zone to show customers the local appointment time.
    tz = ZoneInfo(booking.business.timezone)
    with timezone.override(tz):
        body = render_to_string(
            f"notifications/{template}.txt",
            {"booking": booking, "local_start": booking.starts_at.astimezone(tz)},
        )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])


def booking_confirmed(booking: Booking) -> None:
    _send(
        "booking_confirmed",
        f"Booking confirmed: {booking.service.name}",
        booking,
        booking.customer.email,
    )
    _send(
        "provider_new_booking",
        f"New booking: {booking.service.name}",
        booking,
        booking.business.owner.email,
    )


def booking_cancelled(booking: Booking) -> None:
    for recipient in {booking.customer.email, booking.business.owner.email}:
        _send("booking_cancelled", f"Booking cancelled: {booking.service.name}", booking, recipient)


def booking_rescheduled(booking: Booking) -> None:
    for recipient in {booking.customer.email, booking.business.owner.email}:
        _send("booking_rescheduled", f"Booking moved: {booking.service.name}", booking, recipient)


def booking_reminder(booking: Booking) -> None:
    _send("booking_reminder", f"Reminder: {booking.service.name}", booking, booking.customer.email)
