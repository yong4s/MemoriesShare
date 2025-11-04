from datetime import date
from datetime import timedelta

import factory

from apps.accounts.models import Guest
from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event


class EventFactory(factory.django.DjangoModelFactory):
    """Factory для створення тестових подій"""

    class Meta:
        model = Event

    event_name = factory.Faker('sentence', nb_words=3)
    user = factory.SubFactory(UserFactory)
    description = factory.Faker('paragraph', nb_sentences=5)
    date = factory.LazyFunction(lambda: date.today() + timedelta(days=7))
    is_public = False
    max_guests = None


class FutureEventFactory(EventFactory):
    """Factory для створення майбутніх подій"""

    date = factory.LazyFunction(
        lambda: date.today() + timedelta(days=factory.Faker('pyint', min_value=1, max_value=365).generate())
    )


class PastEventFactory(EventFactory):
    """Factory для створення минулих подій"""

    date = factory.LazyFunction(
        lambda: date.today() - timedelta(days=factory.Faker('pyint', min_value=1, max_value=365).generate())
    )


class LimitedEventFactory(EventFactory):
    """Factory для створення подій з обмеженою кількістю гостей"""

    max_guests = factory.Faker('pyint', min_value=1, max_value=10)


class GuestFactory(factory.django.DjangoModelFactory):
    """Factory для створення тестових гостей"""

    class Meta:
        model = Guest

    event = factory.SubFactory(EventFactory)
    name = factory.Faker('name')
    email = factory.Faker('email')
    phone_number = factory.LazyFunction(
        lambda: f'+380{factory.Faker("random_int", min=500000000, max=999999999).generate()}'
    )
    dietary_preferences = factory.Faker('sentence', nb_words=3)
    rsvp_status = 'pending'


class AcceptedGuestFactory(GuestFactory):
    """Factory для створення підтверджених гостей"""

    rsvp_status = 'accepted'


class DeclinedGuestFactory(GuestFactory):
    """Factory для створення відмовлених гостей"""

    rsvp_status = 'declined'


class PendingGuestFactory(GuestFactory):
    """Factory для створення очікуючих гостей"""

    rsvp_status = 'pending'


class RespondedGuestFactory(GuestFactory):
    """Factory для створення гостей що відповіли"""

    rsvp_status = 'accepted'
    responded_at = factory.Faker('date_time_this_year')


class InvitedGuestFactory(GuestFactory):
    """Factory для створення запрошених гостей"""

    invitation_sent_at = factory.Faker('date_time_this_year')
