from django.test import TestCase, override_settings
from unittest.mock import patch
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import jwt

from . import utils
from .models import Order


class JwtAuthHeaderTests(TestCase):
    """Tests for the ``jwt_auth_header`` helper."""

    def test_header_signs_with_private_key(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("dummykey")
        fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with override_settings(
            HDFC_SMART={
                "PRIVATE_KEY_PATH": tmp.name,
                "KEY_UUID": "uuid",
                "PAYMENT_PAGE_CLIENT_ID": "client",
                "BASE_URL": "https://example.com",
            }
        ), patch("jwt.encode", return_value="tok") as encode, patch(
            "payment.utils.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = fixed_now
            header = utils.jwt_auth_header()

        encode.assert_called_once_with(
            {
                "iss": "client",
                "aud": "https://example.com",
                "iat": int(fixed_now.timestamp()),
                "exp": int((fixed_now + timedelta(minutes=5)).timestamp()),
                "key_uuid": "uuid",
                "payment_page_client_id": "client",
            },
            "dummykey",
            algorithm="RS256",
        )
        self.assertEqual(header, "Bearer tok")
 

class StartPaymentErrorTests(TestCase):
    def test_non_200_response_saved_to_order(self):
        class FakeResponse:
            status_code = 500
            text = "server error"

        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("dummykey")

        settings_dict = {
            "BASE_URL": "https://example.com",
            "MERCHANT_ID": "merchant",
            "PAYMENT_PAGE_CLIENT_ID": "client",
            "RESPONSE_KEY": "resp",
            "RETURN_URL": "https://example.com/return",
            "PRIVATE_KEY_PATH": tmp.name,
            "KEY_UUID": "uuid",
        }

        with override_settings(HDFC_SMART=settings_dict), \
            patch("payment.views.requests.post", return_value=FakeResponse()) as post, \
            patch("jwt.encode", return_value="tok"):
            with self.assertLogs("payment.views", level="ERROR") as cm:
                resp = self.client.get("/payment/hdfc/start/?amount=100")

        self.assertEqual(resp.status_code, 400)
        order = Order.objects.get()
        self.assertEqual(order.raw_resp, {"status_code": 500, "text": "server error"})
        self.assertIn(order.order_id, cm.output[0])

        post.assert_called_once()
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer tok")


class VerifyResponseJwtTests(TestCase):
    def test_verifies_with_public_key(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("pubkey")
        with override_settings(HDFC_SMART={"PUBLIC_KEY_PATH": tmp.name}), patch(
            "jwt.decode", return_value={"ok": True}
        ) as decode:
            payload = utils.verify_response_jwt("tok")
        decode.assert_called_once_with("tok", "pubkey", algorithms=["RS256"])
        self.assertEqual(payload, {"ok": True})

    def test_returns_none_on_error(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("pubkey")
        with override_settings(HDFC_SMART={"PUBLIC_KEY_PATH": tmp.name}), patch(
            "jwt.decode", side_effect=jwt.PyJWTError
        ):
            self.assertIsNone(utils.verify_response_jwt("tok"))


class HdfcReturnJwtVerificationTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(order_id="ORD1", amount=Decimal("100.00"), status="processing")

    def test_invalid_jwt_marks_failed(self):
        data = {
            "merchant_id": "m",
            "order_id": self.order.order_id,
            "amount": "100.00",
            "status": "SUCCESS",
            "signature": "sig",
            "jwt": "tok",
        }
        with patch("payment.views.verify_hmac", return_value=True), patch(
            "payment.views.verify_response_jwt", return_value=None
        ) as verify_jwt:
            self.client.post("/payment/hdfc/return/", data)
        verify_jwt.assert_called_once_with("tok")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "failed")

    def test_valid_jwt_marks_paid(self):
        data = {
            "merchant_id": "m",
            "order_id": self.order.order_id,
            "amount": "100.00",
            "status": "SUCCESS",
            "signature": "sig",
            "jwt": "tok",
        }
        with patch("payment.views.verify_hmac", return_value=True), patch(
            "payment.views.verify_response_jwt", return_value={}
        ):
            self.client.post("/payment/hdfc/return/", data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")
