import random
import uuid
from datetime import date
from datetime import timedelta

import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.events.models import Event
from apps.events.models.event_participant import EventParticipant
from apps.events.models.invite_link_event import InviteEventLink


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    event_name = factory.Faker('sentence', nb_words=3)
    event_uuid = factory.LazyFunction(uuid.uuid4)
    description = factory.Faker('paragraph', nb_sentences=5)
    date = factory.LazyFunction(lambda: date.today() + timedelta(days=7))
    is_public = False

    @factory.post_generation
    def with_owner(self, create, extracted, **kwargs):
        """Optionally attach an OWNER participant.

        Usage:
            EventFactory(with_owner=user)             # uses given user
            EventFactory(with_owner=True)             # creates a new UserFactory
            EventFactory()                            # no owner participant
        """
        if not create or not extracted:
            return

        owner = UserFactory() if extracted is True else extracted
        EventParticipantFactory(event=self, user=owner, as_owner=True)


class FutureEventFactory(EventFactory):
    date = factory.LazyFunction(lambda: date.today() + timedelta(days=random.randint(1, 365)))


class PastEventFactory(EventFactory):
    date = factory.LazyFunction(lambda: date.today() - timedelta(days=random.randint(1, 365)))


class EventParticipantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventParticipant

    event = factory.SubFactory(EventFactory)
    user = factory.SubFactory(UserFactory)
    role = EventParticipant.Role.GUEST
    rsvp_status = EventParticipant.RsvpStatus.PENDING

    class Params:
        as_owner = factory.Trait(
            role=EventParticipant.Role.OWNER,
            rsvp_status=EventParticipant.RsvpStatus.ACCEPTED,
        )
        as_moderator = factory.Trait(role=EventParticipant.Role.MODERATOR)
        as_guest = factory.Trait(role=EventParticipant.Role.GUEST)
        as_attending = factory.Trait(rsvp_status=EventParticipant.RsvpStatus.ACCEPTED)
        as_declined = factory.Trait(rsvp_status=EventParticipant.RsvpStatus.DECLINED)
        as_pending = factory.Trait(rsvp_status=EventParticipant.RsvpStatus.PENDING)
        as_tentative = factory.Trait(rsvp_status=EventParticipant.RsvpStatus.TENTATIVE)
        as_maybe = factory.Trait(rsvp_status=EventParticipant.RsvpStatus.MAYBE)
        as_canceled = factory.Trait(rsvp_status=EventParticipant.RsvpStatus.CANCELED)
        as_confirmed_plus_one = factory.Trait(rsvp_status=EventParticipant.RsvpStatus.CONFIRMED_PLUS_ONE)


class InviteEventLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InviteEventLink

    event = factory.SubFactory(EventFactory)
    invite_token = factory.LazyFunction(uuid.uuid4)
    max_uses = 50
    used_count = 0
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))

    class Params:
        expired = factory.Trait(expires_at=factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1)))
        exhausted = factory.Trait(used_count=factory.LazyAttribute(lambda obj: obj.max_uses))
        revoked = factory.Trait(expires_at=factory.LazyFunction(timezone.now))
