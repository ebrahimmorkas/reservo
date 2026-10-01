from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from apps.catalog.tests.factories import BusinessFactory, ServiceFactory
from apps.scheduling.availability import compute_slots, get_available_slots, is_slot_available
from apps.scheduling.tests.factories import TimeOffFactory, WorkingHoursFactory

pytestmark = pytest.mark.django_db

MONDAY = date(2030, 1, 7)
LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)


def at(hour: int, minute: int = 0, tz=UTC, day: date = MONDAY) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=tz)


@pytest.fixture
def service():
    service = ServiceFactory(duration_minutes=60)
    WorkingHoursFactory(business=service.business, weekday=0, start_time=time(9), end_time=time(12))
    return service


def test_slots_step_through_working_window(service):
    slots = compute_slots(service, MONDAY)

    assert slots[0] == at(9)
    assert slots[-1] == at(11)  # last start where a 60 min appointment still fits
    assert len(slots) == 9  # 15 minute steps from 09:00 to 11:00


def test_no_slots_on_closed_day(service):
    assert compute_slots(service, date(2030, 1, 8)) == []


def test_buffer_time_is_reserved_after_appointment(service):
    service.buffer_minutes = 30
    service.save()

    assert compute_slots(service, MONDAY)[-1] == at(10, 30)


def test_time_off_removes_overlapping_slots(service):
    TimeOffFactory(business=service.business, starts_at=at(10), ends_at=at(10, 30))

    slots = compute_slots(service, MONDAY)

    assert at(9) in slots
    assert at(9, 15) not in slots  # would end at 10:15, inside the time off
    assert at(10, 30) in slots


def test_multiple_windows_per_day(service):
    WorkingHoursFactory(
        business=service.business, weekday=0, start_time=time(14), end_time=time(15)
    )

    assert at(14) in compute_slots(service, MONDAY)


def test_slots_respect_business_timezone():
    business = BusinessFactory(timezone="America/New_York")
    service = ServiceFactory(business=business, duration_minutes=60)
    WorkingHoursFactory(business=business, weekday=0, start_time=time(9), end_time=time(10))

    slots = compute_slots(service, MONDAY)

    assert slots == [at(9, tz=ZoneInfo("America/New_York"))]
    assert slots[0].astimezone(UTC).hour == 14


def test_min_notice_hides_slots_too_close_to_now(service, settings):
    settings.RESERVO_MIN_NOTICE_MINUTES = 60

    slots = get_available_slots(service, MONDAY, now=at(9, 30))

    assert slots[0] == at(10, 30)


def test_cache_is_invalidated_when_time_off_is_added(service):
    assert at(9) in get_available_slots(service, MONDAY, now=LONG_AGO)

    TimeOffFactory(business=service.business, starts_at=at(9), ends_at=at(12))

    assert get_available_slots(service, MONDAY, now=LONG_AGO) == []


def test_is_slot_available(service):
    assert is_slot_available(service, at(9), now=LONG_AGO)
    assert not is_slot_available(service, at(9, 5), now=LONG_AGO)  # not on the 15 min grid
    assert not is_slot_available(service, at(11, 30), now=LONG_AGO)  # does not fit
