import zoneinfo
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


def validate_timezone(value: str) -> None:
    if value not in zoneinfo.available_timezones():
        raise ValidationError(f"'{value}' is not a valid IANA time zone.")


class Business(TimeStampedModel):
    """A bookable business (salon, clinic, studio, ...) owned by a provider."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="businesses"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    timezone = models.CharField(max_length=64, default="UTC", validators=[validate_timezone])
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "businesses"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self) -> str:
        base = slugify(self.name)[:120] or "business"
        slug, counter = base, 2
        while Business.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug


class Service(TimeStampedModel):
    """Something a customer can book, e.g. "Haircut - 30 min"."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(8 * 60)]
    )
    buffer_minutes = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(120)],
        help_text="Cleanup/preparation time blocked after each appointment.",
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["business", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "name"], name="unique_service_per_business"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.business})"

    @property
    def blocked_minutes(self) -> int:
        return self.duration_minutes + self.buffer_minutes
