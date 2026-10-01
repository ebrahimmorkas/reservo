from decimal import Decimal

import factory

from apps.accounts.tests.factories import UserFactory
from apps.catalog.models import Business, Service


class BusinessFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Business

    owner = factory.SubFactory(UserFactory, role="provider")
    name = factory.Sequence(lambda n: f"Studio {n}")
    timezone = "UTC"


class ServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Service

    business = factory.SubFactory(BusinessFactory)
    name = factory.Sequence(lambda n: f"Service {n}")
    duration_minutes = 30
    buffer_minutes = 0
    price = Decimal("25.00")
