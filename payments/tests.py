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
