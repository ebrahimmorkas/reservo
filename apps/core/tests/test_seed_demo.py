import pytest
from django.core.management import call_command

from apps.catalog.models import Business


@pytest.mark.django_db
def test_seed_demo_is_idempotent():
    call_command("seed_demo")
    call_command("seed_demo")

    business = Business.objects.get()
    assert business.services.count() == 3
    assert business.working_hours.count() == 12
