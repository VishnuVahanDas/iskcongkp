from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "status", "amount", "currency", "customer_id", "created_at", "updated_at")
    search_fields = ("order_id", "bank_order_id", "customer_id", "customer_email", "txn_id")
    list_filter = ("status", "currency", "refunded", "created_at")
    readonly_fields = ("created_at", "updated_at", "last_status_payload", "sdk_payload")
