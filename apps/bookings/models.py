from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.catalog.models import Business, Service
from apps.core.models import TimeStampedModel


class BookingQuerySet(models.QuerySet):
    def active(self):
        """Bookings that occupy the calendar."""
        return self.filter(status=Booking.Status.CONFIRMED)

    def overlapping(self, start, end):
        return self.filter(starts_at__lt=end, blocked_until__gt=start)

    def visible_to(self, user):
        return self.filter(Q(customer=user) | Q(business__owner=user))


class Booking(TimeStampedModel):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No-show"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    business = models.ForeignKey(Business, on_delete=models.PROTECT, related_name="bookings")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    blocked_until = models.DateTimeField(
        help_text="End of the appointment including the service buffer."
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CONFIRMED)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Price snapshot at booking time."
    )
    notes = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ["-starts_at"]
        indexes = [
            models.Index(fields=["business", "starts_at"]),
            models.Index(fields=["customer", "starts_at"]),
            models.Index(fields=["status", "starts_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="booking_ends_after_start"
            ),
            models.CheckConstraint(
                condition=Q(blocked_until__gte=F("ends_at")), name="booking_block_covers_end"
            ),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.service.name} @ {self.starts_at:%Y-%m-%d %H:%M}"
