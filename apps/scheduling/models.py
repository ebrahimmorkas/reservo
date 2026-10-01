from django.db import models
from django.db.models import F, Q

from apps.catalog.models import Business
from apps.core.models import TimeStampedModel


class WorkingHours(TimeStampedModel):
    """A recurring weekly opening window. A day may have several windows (e.g. lunch break)."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0
        TUESDAY = 1
        WEDNESDAY = 2
        THURSDAY = 3
        FRIDAY = 4
        SATURDAY = 5
        SUNDAY = 6

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="working_hours")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["business", "weekday", "start_time"]
        verbose_name_plural = "working hours"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")), name="working_hours_end_after_start"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.business} {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class TimeOff(TimeStampedModel):
    """A one-off period when the business cannot take bookings (holiday, sick day, ...)."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="time_off")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["business", "starts_at"]
        verbose_name_plural = "time off"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="time_off_end_after_start"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.business} off {self.starts_at:%Y-%m-%d %H:%M}"
