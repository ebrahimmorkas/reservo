from datetime import timedelta

import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.bookings.models import Booking
from apps.catalog.tests.factories import ServiceFactory


class BookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Booking

    customer = factory.SubFactory(UserFactory)
    service = factory.SubFactory(ServiceFactory)
    business = factory.SelfAttribute("service.business")
    starts_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=2))
    ends_at = factory.LazyAttribute(
        lambda o: o.starts_at + timedelta(minutes=o.service.duration_minutes)
    )
    blocked_until = factory.LazyAttribute(
        lambda o: o.ends_at + timedelta(minutes=o.service.buffer_minutes)
    )
    price = factory.SelfAttribute("service.price")
