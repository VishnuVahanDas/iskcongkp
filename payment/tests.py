from django.test import TestCase, override_settings
from unittest.mock import patch
import tempfile

from . import utils
from .models import Order


class JwtAuthHeaderTests(TestCase):
    """Tests for the ``jwt_auth_header`` helper."""

    def test_header_signs_with_private_key(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("dummykey")
        with override_settings(
            HDFC_SMART={
                "PRIVATE_KEY_PATH": tmp.name,
                "KEY_UUID": "uuid",
                "PAYMENT_PAGE_CLIENT_ID": "client",
            }
        ), patch("jwt.encode", return_value="tok") as encode:
            header = utils.jwt_auth_header()

        encode.assert_called_once_with(
            {
                "key_uuid": "uuid",
                "payment_page_client_id": "client",
            },
            "dummykey",
            algorithm="RS256",
        )
        self.assertEqual(header, "Bearer tok")
 

class StartPaymentErrorTests(TestCase):
    @override_settings(
        HDFC_SMART={
            "BASE_URL": "https://example.com",
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

        with patch("payment.views.requests.post", return_value=FakeResponse()), \
            patch("payment.views.jwt_auth_header", return_value="Bearer tok"):
            with self.assertLogs("payment.views", level="ERROR") as cm:
                resp = self.client.get("/payment/hdfc/start/?amount=100")

        self.assertEqual(resp.status_code, 400)
        order = Order.objects.get()
        self.assertEqual(order.raw_resp, {"status_code": 500, "text": "server error"})
        self.assertIn(order.order_id, cm.output[0])
