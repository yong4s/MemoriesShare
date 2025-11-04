from django.test import TestCase

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory


class EmailCaseInsensitiveTestCase(TestCase):
    def test_email_insensitive(self):
        UserFactory(email='test.User@MAIL.com')

        cases = (
            'test.User@MAIL.com',
            'test.user@mail.com',
            'TEST.USER@MAIL.COM',
        )

        for _search_email in cases:
            with self.subTest(_search_email):
                self.assertTrue(User.objects.filter(email=_search_email).exists())
                self.assertTrue(User.objects.filter(email__iexact=_search_email).exists())
                self.assertTrue(User.objects.filter(email__exact=_search_email).exists())
