import base64

from django.test import TestCase, override_settings
from unittest.mock import patch

from . import utils
from .models import Order


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
 

class StartPaymentErrorTests(TestCase):
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
    def test_non_200_response_saved_to_order(self):
        class FakeResponse:
            status_code = 500
            text = "server error"

        with patch("payment.views.requests.post", return_value=FakeResponse()):
            with self.assertLogs("payment.views", level="ERROR") as cm:
                resp = self.client.get("/payment/hdfc/start/?amount=100")

        self.assertEqual(resp.status_code, 400)
        order = Order.objects.get()
        self.assertEqual(order.raw_resp, {"status_code": 500, "text": "server error"})
        self.assertIn(order.order_id, cm.output[0])
