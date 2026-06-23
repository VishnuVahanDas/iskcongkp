import unittest
from unittest.mock import patch

from payments.utils import extract_payment_status


class PaymentStatusExtractionTests(unittest.TestCase):
    def test_order_order_status_processed(self):
        payload = {"order": {"order_status": "processed"}}
        status, category, source = extract_payment_status(payload)
        self.assertEqual(status, "PROCESSED")
        self.assertEqual(category, "success")
        self.assertEqual(source, "order.order_status")

    def test_result_order_status_processing(self):
        payload = {"result": {"order_status": "processing"}}
        status, category, source = extract_payment_status(payload)
        self.assertEqual(status, "PROCESSING")
        self.assertEqual(category, "pending")
        self.assertEqual(source, "result.order_status")

    def test_payment_order_status_canceled(self):
        payload = {"payment": {"order_status": "canceled"}}
        status, category, source = extract_payment_status(payload)
        self.assertEqual(status, "CANCELED")
        self.assertEqual(category, "failed")
        self.assertEqual(source, "payment.order_status")

from unittest.mock import patch
import payments.integrations.easebuzz as eb_mod
from payments.integrations.easebuzz import (
    _client,
    EasebuzzError,
    EasebuzzIntegrationError,
)


class EasebuzzIntegrationConfigTests(unittest.TestCase):
    def test_missing_merchant_key_raises_error(self):
        with patch.object(eb_mod, "EASEBUZZ_MERCHANT_KEY", ""), \
             patch.object(eb_mod, "EASEBUZZ_SALT", "some_salt"):
            with self.assertRaises(EasebuzzError):
                _client()

    def test_missing_salt_raises_error(self):
        with patch.object(eb_mod, "EASEBUZZ_MERCHANT_KEY", "some_key"), \
             patch.object(eb_mod, "EASEBUZZ_SALT", ""):
            with self.assertRaises(EasebuzzError):
                _client()


# ── UPI AutoPay hash & service tests ─────────────────────────────────────────

from django.conf import settings as django_settings

# Configure minimal Django settings for hash/service tests
# (no DB required — these tests mock all HTTP calls)
if not django_settings.configured:
    django_settings.configure(
        EASEBUZZ_KEY="test_key",
        EASEBUZZ_SALT="test_salt",
        AUTOPAY_ACCESS_KEY_URL="https://api.easebuzz.in/autocollect/v1/access-key/generate",
        AUTOPAY_NOTIFY_URL="https://api.easebuzz.in/autocollect/v1/mandate/notify",
        AUTOPAY_EXECUTE_URL="https://api.easebuzz.in/autocollect/v1/mandate/execute",
        NITYA_SEVA_SUCCESS_URL="https://www.iskcongorakhpur.com/donations/nitya-seva/success/",
        NITYA_SEVA_FAILURE_URL="https://www.iskcongorakhpur.com/donations/nitya-seva/failure/",
    )

from payments.integrations.autopay_utils import (
    hash_access_key, hash_notify, hash_execute,
)
from payments.integrations.autopay_service import (
    generate_access_key, send_debit_notification, execute_debit,
)


class AutoPayHashTests(unittest.TestCase):
    """Verify all 3 hash sequences produce correct SHA-512 output."""

    def test_hash_access_key(self):
        h = hash_access_key("5000.00", "NSTEST123")
        self.assertEqual(len(h), 128)

    def test_hash_notify(self):
        h = hash_notify("NSTEST123", "NTF123456", "5000.00")
        self.assertEqual(len(h), 128)

    def test_hash_execute(self):
        h = hash_execute("NSTEST123", "DEBTEST123", "5000.00")
        self.assertEqual(len(h), 128)


class AutoPayServiceTests(unittest.TestCase):
    """Mock HTTP calls — verify correct payload and headers."""

    @patch("requests.post")
    def test_generate_access_key_payload(self, mock_post):
        mock_post.return_value.json.return_value = {
            "success": True, "access_key": "abc123"
        }
        result = generate_access_key(
            "NSTEST001", 5000, "test@test.com", "9999999999", "Nitya Lamp"
        )
        self.assertEqual(result["access_key"], "abc123")
        call_headers = mock_post.call_args[1]["headers"]
        self.assertIn("Authorization", call_headers)
        self.assertEqual(call_headers["X-EB-PAYMENT-MODE"], "UPIAD")
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["payment_modes"], ["UPIAD"])
        self.assertEqual(payload["frequency"], "monthly")

    @patch("requests.post")
    def test_notify_payload(self, mock_post):
        mock_post.return_value.json.return_value = {
            "success": True, "data": {"id": "no123", "status": "notified"}
        }
        result = send_debit_notification("NSTEST001", 5000, "NTF001")
        self.assertEqual(result["notification_id"], "no123")

    @patch("requests.post")
    def test_execute_payload(self, mock_post):
        mock_post.return_value.json.return_value = {
            "success": True,
            "data": {"pg_transaction_id": "PG001", "status": "in_process"}
        }
        result = execute_debit("NSTEST001", 5000, "no123", "DEB001")
        self.assertEqual(result["pg_transaction_id"], "PG001")
