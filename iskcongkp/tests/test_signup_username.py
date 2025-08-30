from django.test import TestCase, override_settings

from iskcongkp.forms import SignUpForm


@override_settings(
    DEBUG=False,
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
)
class UsernameGenerationTests(TestCase):
    def test_incremental_usernames_generated(self):
        form1 = SignUpForm(
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john1@example.com",
                "mobile": "1234567890",
                "password1": "complexpass123",
                "password2": "complexpass123",
            }
        )
        self.assertTrue(form1.is_valid(), form1.errors)
        user1 = form1.save()
        self.assertEqual(user1.username, "john.doe")

        form2 = SignUpForm(
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john2@example.com",
                "mobile": "1234567891",
                "password1": "complexpass123",
                "password2": "complexpass123",
            }
        )
        self.assertTrue(form2.is_valid(), form2.errors)
        user2 = form2.save()
        self.assertEqual(user2.username, "john.doe1")

        form3 = SignUpForm(
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john3@example.com",
                "mobile": "1234567892",
                "password1": "complexpass123",
                "password2": "complexpass123",
            }
        )
        self.assertTrue(form3.is_valid(), form3.errors)
        user3 = form3.save()
        self.assertEqual(user3.username, "john.doe2")

