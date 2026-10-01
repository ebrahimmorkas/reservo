from functools import partial

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.scheduling.availability import invalidate_availability

from .models import Booking


@receiver(post_save, sender=Booking)
def bust_availability_cache(sender, instance: Booking, **kwargs) -> None:
    transaction.on_commit(partial(invalidate_availability, instance.business_id))
