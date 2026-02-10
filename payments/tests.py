import unittest

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
from payments.integrations.easebuzz import _credentials, EasebuzzIntegrationError


class EasebuzzIntegrationConfigTests(unittest.TestCase):
    def test_credentials_require_key_and_salt(self):
        with patch.dict("os.environ", {}, clear=False):
            with self.assertRaises(EasebuzzIntegrationError):
                _credentials()

    def test_invalid_env_is_rejected(self):
        with patch.dict(
            "os.environ",
            {
                "EASEBUZZ_MERCHANT_KEY": "k",
                "EASEBUZZ_SALT": "s",
                "EASEBUZZ_ENV": "staging",
            },
            clear=False,
        ):
            with self.assertRaises(EasebuzzIntegrationError):
                _credentials()
