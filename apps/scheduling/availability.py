"""Slot computation engine.

Given a service and a calendar day (in the business' local time zone) this module
produces the list of start times a customer can book. A slot is offered when the
whole ``duration + buffer`` window fits inside a working-hours window and does
not overlap any *busy* interval (time off, existing bookings).

Raw slots are cached per service/day. The cache key embeds a per-business
"version" that is bumped whenever anything affecting availability changes, so
stale entries are never served and no explicit key deletion is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.bookings.models import Booking
from apps.catalog.models import Business, Service

from .models import TimeOff

CACHE_TTL_SECONDS = 60 * 60


@dataclass(frozen=True, slots=True)
class Interval:
    start: datetime
    end: datetime

    def overlaps(self, other: Interval) -> bool:
        return self.start < other.end and other.start < self.end


def busy_intervals(
    business: Business,
    start: datetime,
    end: datetime,
    *,
    exclude_booking: Booking | None = None,
) -> list[Interval]:
    """All intervals within ``[start, end)`` during which the business is unavailable."""
    time_off = TimeOff.objects.filter(business=business, starts_at__lt=end, ends_at__gt=start)
    bookings = Booking.objects.active().filter(business=business).overlapping(start, end)
    if exclude_booking is not None:
        bookings = bookings.exclude(pk=exclude_booking.pk)
    return [Interval(t.starts_at, t.ends_at) for t in time_off] + [
        Interval(b.starts_at, b.blocked_until) for b in bookings
    ]


def working_windows(business: Business, day: date) -> list[Interval]:
    tz = ZoneInfo(business.timezone)
    return [
        Interval(
            datetime.combine(day, hours.start_time, tzinfo=tz),
            datetime.combine(day, hours.end_time, tzinfo=tz),
        )
        for hours in business.working_hours.filter(weekday=day.weekday())
    ]


def compute_slots(
    service: Service, day: date, *, exclude_booking: Booking | None = None
) -> list[datetime]:
    """Compute every bookable start time for ``service`` on ``day`` (ignores 'now').

    ``exclude_booking`` lets a booking being rescheduled ignore its own current slot.
    """
    windows = working_windows(service.business, day)
    if not windows:
        return []

    step = timedelta(minutes=settings.RESERVO_SLOT_STEP_MINUTES)
    length = timedelta(minutes=service.blocked_minutes)
    busy = busy_intervals(
        service.business,
        min(w.start for w in windows),
        max(w.end for w in windows),
        exclude_booking=exclude_booking,
    )

    slots: set[datetime] = set()
    for window in windows:
        cursor = window.start
        while cursor + length <= window.end:
            candidate = Interval(cursor, cursor + length)
            if not any(candidate.overlaps(b) for b in busy):
                slots.add(cursor)
            cursor += step
    return sorted(slots)


def get_available_slots(
    service: Service, day: date, *, now: datetime | None = None
) -> list[datetime]:
    """Cached slots for a day, excluding anything earlier than the minimum notice period."""
    version = availability_version(service.business_id)
    key = f"slots:{service.business_id}:v{version}:{service.pk}:{day.isoformat()}"
    slots = cache.get(key)
    if slots is None:
        slots = compute_slots(service, day)
        cache.set(key, slots, CACHE_TTL_SECONDS)

    earliest = (now or timezone.now()) + timedelta(minutes=settings.RESERVO_MIN_NOTICE_MINUTES)
    return [slot for slot in slots if slot >= earliest]


def is_slot_available(service: Service, start: datetime, *, now: datetime | None = None) -> bool:
    local_day = start.astimezone(ZoneInfo(service.business.timezone)).date()
    return start in get_available_slots(service, local_day, now=now)


def _version_key(business_id: int) -> str:
    return f"availability-version:{business_id}"


def availability_version(business_id: int) -> int:
    return cache.get_or_set(_version_key(business_id), 1, timeout=None)


def invalidate_availability(business_id: int) -> None:
    """Bump the business' cache version so every cached slot list becomes unreachable."""
    key = _version_key(business_id)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 2, timeout=None)
