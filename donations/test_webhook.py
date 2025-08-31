import json
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Donor, Donation


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class HdfcWebhookTests(TestCase):
    def setUp(self):
        self.donor = Donor.objects.create(
            email='alice@example.com',
            email_norm='alice@example.com'
        )

    def _post(self, payload: dict):
        return self.client.post(
            reverse('donations:hdfc_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_transaction_id_matches_txn_id(self):
        donation = Donation.objects.create(
            donor=self.donor,
            amount=100,
            purpose='Test',
            txn_id='TXN123',
            order_id='ORD999',
        )
        payload = {'transaction': {'id': 'TXN123', 'status': 'SUCCESS'}}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        donation.refresh_from_db()
        self.assertEqual(donation.status, 'SUCCESS')

    def test_transaction_id_matches_order_id(self):
        donation = Donation.objects.create(
            donor=self.donor,
            amount=100,
            purpose='Test',
            txn_id='INT123',
            order_id='GW456',
        )
        payload = {'transaction': {'id': 'GW456', 'status': 'SUCCESS'}}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        donation.refresh_from_db()
        self.assertEqual(donation.status, 'SUCCESS')
