import base64

from django.test import TestCase, override_settings

from . import utils


class BasicAuthHeaderTests(TestCase):
    """Tests for the ``basic_auth_header`` helper."""

    @override_settings(
        HDFC_SMART={
            "BASE_URL": "https://example.com",
            "API_KEY": "api",
            "MERCHANT_ID": "merchant",
            "CLIENT_ID": "client",
            "RESPONSE_KEY": "resp",
            "RETURN_URL": "https://example.com/return",
        }
    )
    def test_header_with_client_id(self):
        """Auth header uses ``client_id:api_key`` when client ID provided."""

        expected = "Basic " + base64.b64encode(b"client:api").decode()
        self.assertEqual(utils.basic_auth_header(), expected)

    @override_settings(
        HDFC_SMART={
            "BASE_URL": "https://example.com",
            "API_KEY": "api",
            "MERCHANT_ID": "merchant",
            "CLIENT_ID": "",
            "RESPONSE_KEY": "resp",
            "RETURN_URL": "https://example.com/return",
        }
    )
    def test_header_without_client_id(self):
        """Auth header falls back to ``api_key:`` when client ID missing."""

        expected = "Basic " + base64.b64encode(b"api:").decode()
        self.assertEqual(utils.basic_auth_header(), expected)

