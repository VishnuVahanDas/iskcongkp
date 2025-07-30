from django.test import SimpleTestCase, override_settings


@override_settings(
    DEBUG=False,
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
)
class ErrorHandlerTests(SimpleTestCase):
    def test_custom_404_template_used(self):
        response = self.client.get('/this-url-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
