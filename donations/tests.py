from django.test import TestCase

from .models import Donor
from .services import get_or_create_donor


class GetOrCreateDonorTests(TestCase):
    def test_longer_name_updates_donor(self):
        donor = Donor.objects.create(name="Bob", email="bob@example.com", email_norm="bob@example.com")

        get_or_create_donor("Robert", "bob@example.com", None, None)
        donor.refresh_from_db()

        self.assertEqual(donor.name, "Robert")

    def test_shorter_name_does_not_override(self):
        donor = Donor.objects.create(name="Robert", email="bob@example.com", email_norm="bob@example.com")

        get_or_create_donor("Bob", "bob@example.com", None, None)
        donor.refresh_from_db()

        self.assertEqual(donor.name, "Robert")
