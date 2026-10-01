from datetime import time

import factory

from apps.catalog.tests.factories import BusinessFactory
from apps.scheduling.models import TimeOff, WorkingHours


class WorkingHoursFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkingHours

    business = factory.SubFactory(BusinessFactory)
    weekday = 0
    start_time = time(9, 0)
    end_time = time(17, 0)


class TimeOffFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TimeOff

    business = factory.SubFactory(BusinessFactory)
    reason = "Holiday"


def open_every_day(business, start=time(9, 0), end=time(17, 0)) -> None:
    for weekday in range(7):
        WorkingHoursFactory(business=business, weekday=weekday, start_time=start, end_time=end)
