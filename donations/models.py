from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone

class Donor(models.Model):
    email = models.EmailField(null=True, blank=True)
    email_norm = models.EmailField(null=True, blank=True, unique=True)
    phone_e164 = models.CharField(
        max_length=16, null=True, blank=True, unique=False,
        validators=[RegexValidator(r'^\+\d{6,15}$')]
    )
    name = models.CharField(max_length=128, blank=True, default="")
    pan = models.CharField(max_length=10, blank=True, default="", db_index=True)
    address_line1 = models.CharField(max_length=128, blank=True, default="")
    address_line2 = models.CharField(max_length=128, blank=True, default="")
    city = models.CharField(max_length=64, blank=True, default="")
    state = models.CharField(max_length=64, blank=True, default="")
    postal_code = models.CharField(max_length=16, blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="IN")
    is_claimed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or self.email or self.phone_e164 or f"Donor#{self.pk}"

class Donation(models.Model):
    STATUS_CHOICES = [
        ("PENDING","PENDING"),
        ("SUCCESS","SUCCESS"),
        ("FAILED","FAILED"),
    ]
    donor = models.ForeignKey(Donor, on_delete=models.PROTECT, related_name="donations")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.CharField(max_length=64, default="General")
    txn_id = models.CharField(max_length=64, unique=True)
    order_id = models.CharField(max_length=64, db_index=True)  # gateway order/session id
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, db_index=True, default="PENDING")
    mode = models.CharField(max_length=32, blank=True, default="")
    gateway_meta = models.JSONField(default=dict, blank=True)
    issued_receipt_no = models.CharField(max_length=32, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.txn_id} {self.status} ₹{self.amount}"

class Receipt(models.Model):
    donation = models.OneToOneField(Donation, on_delete=models.PROTECT, related_name="receipt")
    number = models.CharField(max_length=32, unique=True)
    pdf_path = models.CharField(max_length=256, blank=True, default="")
    issued_at = models.DateTimeField(auto_now_add=True)

class MagicLinkToken(models.Model):
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="magic_links")
    token = models.CharField(max_length=64, db_index=True, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class OtpCode(models.Model):
    """
    Email OR phone OTP (we'll use email OTP as you requested 'magic otp').
    """
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="otps")
    channel = models.CharField(max_length=8, default="email")  # "email" or "sms"
    code = models.CharField(max_length=6, db_index=True)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
