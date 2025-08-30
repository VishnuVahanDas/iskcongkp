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
