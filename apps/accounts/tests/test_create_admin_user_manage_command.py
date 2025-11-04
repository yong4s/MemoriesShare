from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.tests.factories import UserFactory


class CreateAdminUserManageCommandTestCase(TestCase):
    def test_creates_new_admin_user_successfully(self):
        out = StringIO()
        call_command('create_admin_user', stdout=out)
        self.assertIn('Development admin user has been created!', out.getvalue())

        user = get_user_model().objects.get(email='admin@mail.com')

        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_updates_admin_user_successfully(self):
        user = UserFactory(
            email='admin@mail.com',
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )
        out = StringIO()
        call_command('create_admin_user', stdout=out)
        self.assertIn('Development admin user has been created!', out.getvalue())

        user.refresh_from_db()

        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
