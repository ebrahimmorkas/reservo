from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.catalog.models import Service

from .availability import invalidate_availability
from .models import TimeOff, WorkingHours


@receiver([post_save, post_delete], sender=WorkingHours)
@receiver([post_save, post_delete], sender=TimeOff)
@receiver([post_save, post_delete], sender=Service)
def bust_availability_cache(sender, instance, **kwargs) -> None:
    # Invalidate after commit so a concurrent reader cannot re-cache pre-commit data.
    transaction.on_commit(partial(invalidate_availability, instance.business_id))
