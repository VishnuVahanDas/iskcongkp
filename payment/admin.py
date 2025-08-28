from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "status", "amount", "gateway_order_id", "created_at")
    search_fields = ("order_id", "gateway_order_id", "gateway_txn_id")
    readonly_fields = ("raw_req", "raw_resp", "webhook")
    ordering = ("-created_at",)
