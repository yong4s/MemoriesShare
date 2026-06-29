import factory

from apps.accounts.models import CustomUser

TEST_PASSWORD = 'testpassword'  # noqa: S105


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser

    email = factory.Sequence(lambda i: f'test-{i}@test.com'.lower())
    password = factory.PostGenerationMethodCall('set_password', TEST_PASSWORD)
