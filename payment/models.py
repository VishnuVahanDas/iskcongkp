# payment/models.py
from django.db import models

class Order(models.Model):
    STATUS = [("created","Created"),("processing","Processing"),
              ("paid","Paid"),("failed","Failed")]
    order_id = models.CharField(max_length=40, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=40, blank=True)
    currency = models.CharField(max_length=8, default="INR")
    status = models.CharField(max_length=12, choices=STATUS, default="created")
    gateway_order_id = models.CharField(max_length=64, blank=True, null=True)
    gateway_txn_id = models.CharField(max_length=64, blank=True, null=True)
    raw_req = models.JSONField(blank=True, null=True)
    raw_resp = models.JSONField(blank=True, null=True)
    webhook = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
