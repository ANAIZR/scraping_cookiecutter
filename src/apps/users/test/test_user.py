from django.test import TestCase
from src.apps.users.models import User


class UserModelTest(TestCase):
    def setUp(self):

        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser",
            password="testpassword",
        )

    def test_create_user(self):

        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.is_active, True)
        self.assertIsNone(self.user.deleted_at)

    def test_delete_user(self):

        self.user.delete()

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.deleted_at)
        self.assertFalse(self.user.is_active)

    def test_restore_user(self):

        self.user.delete()

        self.user.restore()

        self.user.refresh_from_db()
        self.assertIsNone(self.user.deleted_at)
        self.assertTrue(self.user.is_active)

    def test_is_deleted(self):

        self.assertFalse(self.user.is_deleted())

        self.user.delete()
        self.user.refresh_from_db()

        self.assertTrue(self.user.is_deleted())
