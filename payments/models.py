from django.db import models

class Order(models.Model):
    order_id = models.CharField(max_length=20, unique=True, db_index=True)  # your alnum id
    bank_order_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    status = models.CharField(max_length=32, default="NEW")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="INR")

    customer_id = models.CharField(max_length=64)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=16)

    payment_links_web = models.URLField(blank=True, default="")
    sdk_payload = models.JSONField(blank=True, null=True)

    last_status_payload = models.JSONField(blank=True, null=True)

    txn_id = models.CharField(max_length=128, blank=True, default="")
    payment_method_type = models.CharField(max_length=32, blank=True, default="")
    payment_method = models.CharField(max_length=32, blank=True, default="")
    auth_type = models.CharField(max_length=32, blank=True, default="")
    refunded = models.BooleanField(default=False)
    amount_refunded = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    metadata = models.JSONField(blank=True, null=True)
    order_expiry = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_paid(self) -> bool:
        return (self.status or "").upper() == "CHARGED"

    def __str__(self):
        return f"{self.order_id} ({self.status})"


class NityaSevaAutoCollect(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("expired", "Expired"),
    ]

    # Donor fields
    full_name     = models.CharField(max_length=200)
    mobile        = models.CharField(max_length=10)
    email         = models.EmailField(blank=True)
    seva_type     = models.CharField(max_length=100)
    amount        = models.DecimalField(max_digits=10, decimal_places=2)

    # 80G fields — only populated when wants_80g is True
    wants_80g     = models.BooleanField(default=False)
    pan_number    = models.CharField(max_length=10, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    pincode       = models.CharField(max_length=6, blank=True)

    # InstaCollect virtual account fields
    txnid         = models.CharField(max_length=100, unique=True)
    va_id         = models.CharField(max_length=200, blank=True)
    va_number     = models.CharField(max_length=50, blank=True)
    va_ifsc       = models.CharField(max_length=20, blank=True)
    upi_vpa       = models.CharField(max_length=100, blank=True)
    qr_code_url   = models.URLField(blank=True)
    order_id      = models.CharField(max_length=200, blank=True)

    # Payment tracking
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    last_payment_id = models.CharField(max_length=200, blank=True)
    notes           = models.TextField(blank=True)
    webhook_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ["-created_at"]
        verbose_name = "Nitya Seva InstaCollect"

    def __str__(self):
        return f"{self.txnid} | {self.full_name} | ₹{self.amount} | {self.status}"


class NityaSevaMandate(models.Model):
    STATUS_CHOICES = [
        ("pending",   "Pending"),    # access_key generated, awaiting approval
        ("active",    "Active"),     # mandate approved by devotee
        ("failed",    "Failed"),     # mandate rejected / expired
        ("cancelled", "Cancelled"),  # devotee cancelled
    ]
    DEBIT_STATUS_CHOICES = [
        ("not_initiated", "Not Initiated"),
        ("notified",      "Notified"),
        ("in_process",    "In Process"),
        ("success",       "Success"),
        ("failed",        "Failed"),
    ]

    # Devotee info
    full_name     = models.CharField(max_length=200)
    mobile        = models.CharField(max_length=10)
    email         = models.EmailField(blank=True)
    seva_type     = models.CharField(max_length=100)
    amount        = models.DecimalField(max_digits=10, decimal_places=2)

    # 80G (only stored when wants_80g=True)
    wants_80g     = models.BooleanField(default=False)
    pan_number    = models.CharField(max_length=10, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    pincode       = models.CharField(max_length=6, blank=True)

    # Mandate identifiers
    txnid          = models.CharField(max_length=100, unique=True)
    access_key     = models.CharField(max_length=500, blank=True)
    mandate_status = models.CharField(
                       max_length=20, choices=STATUS_CHOICES, default="pending")
    mandate_start  = models.DateField(null=True, blank=True)
    mandate_end    = models.DateField(null=True, blank=True)

    # Monthly debit tracking
    last_notification_id     = models.CharField(max_length=200, blank=True)
    last_notification_number = models.CharField(max_length=100, blank=True)
    last_debit_number        = models.CharField(max_length=100, blank=True)
    last_debit_status        = models.CharField(
                                max_length=20,
                                choices=DEBIT_STATUS_CHOICES,
                                default="not_initiated")
    last_debit_pg_txnid      = models.CharField(max_length=200, blank=True)
    last_debited_at          = models.DateTimeField(null=True, blank=True)
    total_debits_done        = models.IntegerField(default=0)

    # Webhook and raw data
    mandate_webhook_payload  = models.JSONField(null=True, blank=True)
    debit_webhook_payload    = models.JSONField(null=True, blank=True)
    notes                    = models.TextField(blank=True)
    created_at               = models.DateTimeField(auto_now_add=True)
    updated_at               = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ["-created_at"]
        verbose_name = "Nitya Seva UPI AutoPay Mandate"

    def __str__(self):
        return f"{self.txnid} | {self.full_name} | ₹{self.amount} | {self.mandate_status}"
