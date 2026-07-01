from unittest.mock import Mock
from unittest.mock import patch

from django.db import connection
from django.test.utils import override_settings
from rest_framework_api_key.models import APIKey

from apps.accounts.tests.factories import UserFactory
from apps.events.tests.factories import EventFactory
from apps.events.tests.factories import EventParticipantFactory


class EventTestMixin:
    """Common setup for event tests: two users, two events, owner-attached event."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.event = EventFactory()
        self.other_event = EventFactory()

    def create_api_key(self):
        api_key, key = APIKey.objects.create_key(name='test-api-key')
        return api_key, key

    def setup_api_authentication(self):
        if hasattr(self, 'client'):
            api_key, key = self.create_api_key()
            self.client.credentials(HTTP_X_API_KEY=key)
            return api_key, key
        return None, None

    def add_participant(self, event=None, user=None, **kwargs):
        """Create an EventParticipant on the test event by default."""
        return EventParticipantFactory(
            event=event or self.event,
            user=user or UserFactory(),
            **kwargs,
        )


def mock_s3_service(**kwargs):
    """Create a mock S3Service with default settings."""
    defaults = {
        'folder_exists.return_value': False,
        'create_folder.return_value': True,
        'delete_folder.return_value': True,
        'generate_upload_url.return_value': 'https://s3.example.com/upload',
        'generate_download_url.return_value': 'https://s3.example.com/download',
        'generate_bulk_download_urls.return_value': {},
        'delete_s3_object.return_value': True,
        'get_object_metadata.return_value': {
            'content_type': 'image/jpeg',
            'content_length': 1024,
        },
        'process_uploaded_file.return_value': {
            'processed': True,
            'original': 'test-key',
        },
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
    """Decorator for patching S3Service."""

    def decorator(test_func):
        return patch('apps.events.services.S3Service', return_value=mock_s3_service(**kwargs))(test_func)

    return decorator


def create_test_s3_key(user_id, event_uuid, album_uuid=None, file_uuid=None):
    """Create a test S3 key following the project template."""
    album_uuid = album_uuid or 'test-album-uuid'
    file_uuid = file_uuid or 'test-file-uuid'

    return f'user-bucket-{user_id}/{event_uuid}/{album_uuid}/{file_uuid}'


def assert_no_database_queries(test_case, func, *args, **kwargs):
    """Assert that callable issues zero DB queries."""
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
    """Assert that callable issues at most ``max_queries`` DB queries."""
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
