"""Race-condition test: many threads try to grab the same slot at once.

Row-level locks are only meaningful on PostgreSQL, so this test is skipped on SQLite.
CI runs the suite against PostgreSQL as well.
"""

import threading
from datetime import UTC, datetime, time, timedelta

import pytest
from django.db import connection, connections
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.bookings import services
from apps.bookings.models import Booking
from apps.catalog.tests.factories import ServiceFactory
from apps.scheduling.tests.factories import open_every_day

pytestmark = pytest.mark.skipif(
    connection.vendor != "postgresql", reason="requires PostgreSQL row-level locking"
)


@pytest.mark.django_db(transaction=True)
def test_concurrent_requests_for_same_slot_create_one_booking():
    service = ServiceFactory(duration_minutes=60)
    open_every_day(service.business)
    customers = [UserFactory() for _ in range(8)]
    day = timezone.localdate() + timedelta(days=3)
    slot = datetime.combine(day, time(10), tzinfo=UTC)
    barrier = threading.Barrier(len(customers))
    outcomes: list[str] = []

    def attempt(customer):
        try:
            barrier.wait()
            services.create_booking(customer=customer, service=service, starts_at=slot)
            outcomes.append("ok")
        except services.SlotUnavailable:
            outcomes.append("conflict")
        finally:
            connections.close_all()

    threads = [threading.Thread(target=attempt, args=(c,)) for c in customers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("ok") == 1
    assert outcomes.count("conflict") == len(customers) - 1
    assert Booking.objects.count() == 1
