from datetime import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Business, Service
from apps.scheduling.models import WorkingHours

DEMO_PASSWORD = "demo-pass-123"


class Command(BaseCommand):
    help = "Create a demo provider, business, services, opening hours and customer."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        provider, _ = User.objects.get_or_create(
            email="provider@reservo.dev",
            defaults={"role": User.Role.PROVIDER, "first_name": "Priya"},
        )
        provider.set_password(DEMO_PASSWORD)
        provider.save()

        customer, _ = User.objects.get_or_create(
            email="customer@reservo.dev", defaults={"first_name": "Carlos"}
        )
        customer.set_password(DEMO_PASSWORD)
        customer.save()

        business, _ = Business.objects.get_or_create(
            slug="urban-fade-barbers",
            defaults={
                "owner": provider,
                "name": "Urban Fade Barbers",
                "timezone": "Europe/London",
                "address": "12 High Street, London",
                "description": "Classic cuts and hot towel shaves.",
            },
        )
        for name, minutes, buffer, price in [
            ("Classic Haircut", 30, 10, "25.00"),
            ("Beard Trim", 20, 5, "15.00"),
            ("Haircut & Hot Towel Shave", 60, 15, "45.00"),
        ]:
            Service.objects.get_or_create(
                business=business,
                name=name,
                defaults={
                    "duration_minutes": minutes,
                    "buffer_minutes": buffer,
                    "price": Decimal(price),
                },
            )

        for weekday in range(6):  # Monday - Saturday, lunch break 13:00-14:00
            for start, end in [(time(9), time(13)), (time(14), time(18))]:
                WorkingHours.objects.get_or_create(
                    business=business, weekday=weekday, start_time=start, end_time=end
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready.\n"
                f"  provider: provider@reservo.dev / {DEMO_PASSWORD}\n"
                f"  customer: customer@reservo.dev / {DEMO_PASSWORD}\n"
                f"  business: /api/v1/businesses/{business.slug}/"
            )
        )
