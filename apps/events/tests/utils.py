"""
Утилітні функції для тестування events додатку.
"""

import json
from unittest.mock import Mock
from unittest.mock import patch

from rest_framework_api_key.models import APIKey

from apps.accounts.tests.factories import UserFactory
from apps.events.tests.factories import EventFactory
from apps.events.tests.factories import GuestFactory


class EventTestMixin:
    """Mixin для спрощення тестування подій"""

    def setUp(self):
        """Базова настройка для тестів подій"""
        super().setUp()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.event = EventFactory()
        self.other_event = EventFactory()

    def create_api_key(self):
        """Створює API ключ для тестування"""
        api_key, key = APIKey.objects.create_key(name='test-api-key')
        return api_key, key

    def setup_api_authentication(self):
        """Налаштовує API автентифікацію для клієнта"""
        if hasattr(self, 'client'):
            api_key, key = self.create_api_key()
            self.client.credentials(HTTP_X_API_KEY=key)
            return api_key, key
        return None, None

    def create_guest_for_event(self, event=None, **kwargs):
        """Створює гостя для події"""
        if event is None:
            event = self.event

        defaults = {'event': event, 'name': 'Test Guest', 'email': 'guest@example.com', 'rsvp_status': 'pending'}
        defaults.update(kwargs)

        return GuestFactory(**defaults)

    def create_multiple_guests(self, event=None, count=3, **kwargs):
        """Створює кілька гостей для події"""
        if event is None:
            event = self.event

        guests = []
        for i in range(count):
            guest_kwargs = kwargs.copy()
            if 'email' not in guest_kwargs:
                guest_kwargs['email'] = f'guest{i+1}@example.com'
            if 'name' not in guest_kwargs:
                guest_kwargs['name'] = f'Guest {i+1}'

            guests.append(self.create_guest_for_event(event, **guest_kwargs))

        return guests


def mock_s3_service(**kwargs):
    """Створює мок для S3Service з налаштуваннями за замовчуванням"""
    defaults = {
        'folder_exists.return_value': False,
        'create_folder.return_value': True,
        'delete_folder.return_value': True,
        'generate_upload_url.return_value': 'https://s3.example.com/upload',
        'generate_download_url.return_value': 'https://s3.example.com/download',
        'generate_bulk_download_urls.return_value': {},
        'delete_s3_object.return_value': True,
        'get_object_metadata.return_value': {'content_type': 'image/jpeg', 'content_length': 1024},
        'process_uploaded_file.return_value': {'processed': True, 'original': 'test-key'},
    }

    defaults.update(kwargs)

    mock = Mock()
    for attr, value in defaults.items():
        parts = attr.split('.')
        obj = mock
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)

    return mock


def patch_s3_service(**kwargs):
    """Decorator для патчингу S3Service"""

    def decorator(test_func):
        return patch('apps.events.services.S3Service', return_value=mock_s3_service(**kwargs))(test_func)

    return decorator


def create_test_s3_key(user_id, event_uuid, album_uuid=None, file_uuid=None):
    """Створює тестовий S3 ключ за шаблоном проєкту"""
    album_uuid = album_uuid or 'test-album-uuid'
    file_uuid = file_uuid or 'test-file-uuid'

    return f'user-bucket-{user_id}/{event_uuid}/{album_uuid}/{file_uuid}'


def assert_no_database_queries(test_case, func, *args, **kwargs):
    """Перевіряє, що функція не виконує запити до БД"""
    from django.db import connection
    from django.test.utils import override_settings

    with override_settings(DEBUG=True):
        initial_queries = len(connection.queries)
        func(*args, **kwargs)
        final_queries = len(connection.queries)

        test_case.assertEqual(
            initial_queries,
            final_queries,
            f'Function executed {final_queries - initial_queries} database queries when none expected',
        )


def assert_max_database_queries(test_case, max_queries, func, *args, **kwargs):
    """Перевіряє, що функція виконує не більше заданої кількості запитів до БД"""
    from django.db import connection
    from django.test.utils import override_settings

    with override_settings(DEBUG=True):
        initial_queries = len(connection.queries)
        result = func(*args, **kwargs)
        final_queries = len(connection.queries)

        queries_count = final_queries - initial_queries
        test_case.assertLessEqual(
            queries_count,
            max_queries,
            f'Function executed {queries_count} database queries, expected max {max_queries}',
        )

        return result
