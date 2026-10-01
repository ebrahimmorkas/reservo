import factory

from apps.accounts.models import User

DEFAULT_PASSWORD = "S3cure-pass!"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = User.Role.CUSTOMER
    password = factory.django.Password(DEFAULT_PASSWORD)
