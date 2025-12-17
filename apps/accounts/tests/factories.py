import factory

from apps.accounts.models import User

TEST_PASSWORD = 'testpassword'  # noqa: S105


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda i: f'test-{i}@test.com'.lower())
    password = factory.PostGenerationMethodCall('set_password', TEST_PASSWORD)
