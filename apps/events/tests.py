from datetime import date
from datetime import timedelta
from unittest.mock import Mock
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.factories import TEST_PASSWORD
from apps.accounts.tests.factories import UserFactory

from .models import Event
from .models import Guest

User = get_user_model()


class EventModelTest(TestCase):
    """Тести для моделі Event"""

    def setUp(self):
        self.user = UserFactory()
        self.future_date = date.today() + timedelta(days=7)
        self.past_date = date.today() - timedelta(days=7)

    def test_create_event(self):
        """Тест створення події"""
        event = Event.objects.create(
            event_name='Тестова подія',
            user=self.user,
            description='Опис тестової події з достатньою кількістю символів',
            date=self.future_date,
        )

        self.assertEqual(event.event_name, 'Тестова подія')
        self.assertEqual(event.user, self.user)
        self.assertTrue(event.event_uuid)
        self.assertTrue(event.gallery_url)

    def test_event_validation_short_name(self):
        """Тест валідації короткої назви події"""
        with self.assertRaises(ValidationError):
            event = Event(
                event_name='Аб',
                user=self.user,
                description='Опис тестової події з достатньою кількістю символів',
                date=self.future_date,
            )
            event.full_clean()

    def test_event_validation_short_description(self):
        """Тест валідації короткого опису події"""
        with self.assertRaises(ValidationError):
            event = Event(event_name='Тестова подія', user=self.user, description='Короткий', date=self.future_date)
            event.full_clean()

    def test_event_str_representation(self):
        """Тест строкового представлення події"""
        event = Event.objects.create(
            event_name='Тестова подія',
            user=self.user,
            description='Опис тестової події з достатньою кількістю символів',
            date=self.future_date,
        )
        self.assertIn('Тестова подія', str(event))
        self.assertIn('id=', str(event))

    def test_event_validation_past_date(self):
        """Тест валідації минулої дати події"""
        with self.assertRaises(ValidationError) as context:
            event = Event(
                event_name='Тестова подія',
                user=self.user,
                description='Опис тестової події з достатньою кількістю символів',
                date=self.past_date,
            )
            event.full_clean()

        self.assertIn('date', context.exception.error_dict)

    def test_event_max_guests_validation(self):
        """Тест валідації максимальної кількості гостей"""
        with self.assertRaises(ValidationError):
            event = Event(
                event_name='Тестова подія',
                user=self.user,
                description='Опис тестової події з достатньою кількістю символів',
                date=self.future_date,
                max_guests=0,
            )
            event.full_clean()

    def test_event_properties(self):
        """Тест властивостей події"""
        # Майбутня подія
        future_event = Event.objects.create(
            event_name='Майбутня подія',
            user=self.user,
            description='Опис майбутньої події з достатньою кількістю символів',
            date=self.future_date,
        )
        self.assertTrue(future_event.is_upcoming)
        self.assertFalse(future_event.is_past)

        # Минула подія (створюємо без валідації)
        past_event = Event(
            event_name='Минула подія',
            user=self.user,
            description='Опис минулої події з достатньою кількістю символів',
            date=self.past_date,
        )
        past_event.save()
        self.assertFalse(past_event.is_upcoming)
        self.assertTrue(past_event.is_past)

    def test_event_guest_count_properties(self):
        """Тест властивостей підрахунку гостей"""
        event = Event.objects.create(
            event_name='Тестова подія',
            user=self.user,
            description='Опис тестової події з достатньою кількістю символів',
            date=self.future_date,
            max_guests=5,
        )

        # Створюємо гостей з різними статусами
        Guest.objects.create(event=event, name='Гість 1', email='guest1@example.com', rsvp_status='accepted')
        Guest.objects.create(event=event, name='Гість 2', email='guest2@example.com', rsvp_status='declined')

        self.assertEqual(event.guest_count, 2)
        self.assertEqual(event.accepted_guests_count, 1)
        self.assertTrue(event.can_add_guests())
        self.assertEqual(event.remaining_guest_slots(), 3)

    def test_event_custom_queryset_methods(self):
        """Тест кастомних методів QuerySet"""
        user2 = UserFactory()

        # Створюємо події
        event1 = Event.objects.create(
            event_name='Подія користувача 1',
            user=self.user,
            description='Опис події користувача 1 з достатньою кількістю символів',
            date=self.future_date,
        )
        event2 = Event.objects.create(
            event_name='Подія користувача 2',
            user=user2,
            description='Опис події користувача 2 з достатньою кількістю символів',
            date=self.future_date,
        )

        # Додаємо користувача 1 як гостя до події користувача 2
        Guest.objects.create(event=event2, name=self.user.email, email=self.user.email, rsvp_status='accepted')

        # Тестуємо for_user
        user_events = Event.objects.for_user(self.user.id)
        self.assertEqual(user_events.count(), 2)  # Власна подія + подія як гість

        # Тестуємо upcoming/past
        upcoming_events = Event.objects.upcoming()
        self.assertIn(event1, upcoming_events)
        self.assertIn(event2, upcoming_events)


class GuestModelTest(TestCase):
    """Тести для моделі Guest"""

    def setUp(self):
        self.user = UserFactory()
        self.event = Event.objects.create(
            event_name='Тестова подія',
            user=self.user,
            description='Опис тестової події з достатньою кількістю символів',
            date=date.today() + timedelta(days=7),
        )

    def test_create_guest(self):
        """Тест створення гостя"""
        guest = Guest.objects.create(
            event=self.event,
            name='Тестовий гість',
            email='guest@example.com',
            phone_number='+380501234567',
            dietary_preferences='Вегетаріанець',
            rsvp_status='accepted',
        )

        self.assertEqual(guest.name, 'Тестовий гість')
        self.assertEqual(guest.email, 'guest@example.com')
        self.assertEqual(guest.rsvp_status, 'accepted')

    def test_guest_validation_missing_name(self):
        """Тест валідації відсутності імені"""
        with self.assertRaises(ValidationError):
            guest = Guest(event=self.event, email='guest@example.com', rsvp_status='accepted')
            guest.full_clean()

    def test_guest_validation_missing_email(self):
        """Тест валідації відсутності email"""
        with self.assertRaises(ValidationError):
            guest = Guest(event=self.event, name='Тестовий гість', rsvp_status='accepted')
            guest.full_clean()

    def test_guest_str_representation(self):
        """Тест строкового представлення гостя"""
        guest = Guest.objects.create(
            event=self.event, name='Тестовий гість', email='guest@example.com', rsvp_status='accepted'
        )
        self.assertIn('Тестовий гість', str(guest))
        self.assertIn('Підтверджено', str(guest))  # Перевіряємо локалізований текст

    def test_guest_unique_together_constraint(self):
        """Тест унікальності email в межах події"""
        Guest.objects.create(
            event=self.event, name='Тестовий гість 1', email='guest@example.com', rsvp_status='accepted'
        )

        # Другий гість з тим же email в тій же події має викликати помилку
        with self.assertRaises(Exception):
            Guest.objects.create(
                event=self.event, name='Тестовий гість 2', email='guest@example.com', rsvp_status='pending'
            )

    def test_guest_rsvp_status_choices(self):
        """Тест доступних RSVP статусів"""
        valid_statuses = [
            'accepted',
            'declined',
            'pending',
            'tentative',
            'canceled',
            'no_show',
            'waitlisted',
            'maybe',
            'confirmed_plus_one',
            'declined_with_regret',
        ]

        for status in valid_statuses:
            guest = Guest.objects.create(
                event=self.event, name=f'Гість {status}', email=f'guest_{status}@example.com', rsvp_status=status
            )
            self.assertEqual(guest.rsvp_status, status)

    def test_guest_properties(self):
        """Тест властивостей гостя"""
        # Гість що не відповів
        pending_guest = Guest.objects.create(
            event=self.event, name='Очікуючий гість', email='pending@example.com', rsvp_status='pending'
        )
        self.assertFalse(pending_guest.has_responded)
        self.assertFalse(pending_guest.is_attending)

        # Гість що підтвердив участь
        accepted_guest = Guest.objects.create(
            event=self.event, name='Підтверджений гість', email='accepted@example.com', rsvp_status='accepted'
        )
        self.assertTrue(accepted_guest.has_responded)
        self.assertTrue(accepted_guest.is_attending)

        # Гість що відмовився
        declined_guest = Guest.objects.create(
            event=self.event, name='Відмовлений гість', email='declined@example.com', rsvp_status='declined'
        )
        self.assertTrue(declined_guest.has_responded)
        self.assertFalse(declined_guest.is_attending)

    def test_guest_responded_at_automatic_setting(self):
        """Тест автоматичного встановлення responded_at"""
        guest = Guest.objects.create(
            event=self.event, name='Тестовий гість', email='test@example.com', rsvp_status='pending'
        )
        self.assertIsNone(guest.responded_at)

        # Змінюємо статус
        guest.rsvp_status = 'accepted'
        guest.save()

        # Перезавантажуємо з БД
        guest.refresh_from_db()
        self.assertIsNotNone(guest.responded_at)

    def test_guest_validation_short_name(self):
        """Тест валідації короткого імені"""
        with self.assertRaises(ValidationError):
            guest = Guest(event=self.event, name='А', email='guest@example.com', rsvp_status='accepted')
            guest.full_clean()

    def test_guest_email_normalization(self):
        """Тест нормалізації email"""
        guest = Guest.objects.create(
            event=self.event, name='Тестовий гість', email='GUEST@EXAMPLE.COM', rsvp_status='accepted'
        )
        self.assertEqual(guest.email, 'guest@example.com')

    def test_guest_max_guests_validation(self):
        """Тест валідації максимальної кількості гостей"""
        # Створюємо подію з обмеженням на 1 гостя
        limited_event = Event.objects.create(
            event_name='Обмежена подія',
            user=self.user,
            description='Опис обмеженої події з достатньою кількістю символів',
            date=date.today() + timedelta(days=7),
            max_guests=1,
        )

        # Додаємо першого гостя
        Guest.objects.create(
            event=limited_event, name='Перший гість', email='first@example.com', rsvp_status='accepted'
        )

        # Спроба додати другого гостя має викликати помилку
        with self.assertRaises(ValidationError):
            guest = Guest(event=limited_event, name='Другий гість', email='second@example.com', rsvp_status='accepted')
            guest.full_clean()

    def test_guest_send_invitation(self):
        """Тест методу send_invitation"""
        guest = Guest.objects.create(
            event=self.event, name='Тестовий гість', email='test@example.com', rsvp_status='pending'
        )

        self.assertIsNone(guest.invitation_sent_at)
        guest.send_invitation()

        guest.refresh_from_db()
        self.assertIsNotNone(guest.invitation_sent_at)

    def test_guest_custom_queryset_methods(self):
        """Тест кастомних методів QuerySet для гостей"""
        # Створюємо гостей з різними статусами
        Guest.objects.create(
            event=self.event, name='Підтверджений', email='accepted@example.com', rsvp_status='accepted'
        )
        Guest.objects.create(event=self.event, name='Відмовлений', email='declined@example.com', rsvp_status='declined')
        Guest.objects.create(event=self.event, name='Очікуючий', email='pending@example.com', rsvp_status='pending')

        # Тестуємо методи QuerySet
        self.assertEqual(Guest.objects.accepted().count(), 1)
        self.assertEqual(Guest.objects.declined().count(), 1)
        self.assertEqual(Guest.objects.pending().count(), 1)
        self.assertEqual(Guest.objects.for_event(self.event.id).count(), 3)
