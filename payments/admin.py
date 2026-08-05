from django.contrib import admin
from .models import Order, NityaSevaAutoCollect, NityaSevaMandate


class NoBulkDeleteAdminMixin:
    """
    Financial/transaction records should not be bulk-deletable from the
    admin UI — there's no reconciliation trail for EaseBuzz-sourced data
    if a row disappears. Deletion (if ever needed) should go through a
    reviewed, logged, out-of-band process instead.
    """

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(Order)
class OrderAdmin(NoBulkDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("order_id", "status", "amount", "currency", "customer_id", "created_at", "updated_at")
    search_fields = ("order_id", "bank_order_id", "customer_id", "customer_email", "txn_id")
    list_filter = ("status", "currency", "refunded", "created_at")
    readonly_fields = ("created_at", "updated_at", "last_status_payload", "sdk_payload")


@admin.register(NityaSevaAutoCollect)
class NityaSevaAutoCollectAdmin(NoBulkDeleteAdminMixin, admin.ModelAdmin):
    list_display  = ["txnid", "full_name", "mobile", "seva_type", "amount", "status", "wants_80g", "created_at"]
    list_filter   = ["status", "seva_type", "wants_80g"]
    search_fields = ["txnid", "full_name", "mobile", "pan_number", "va_number", "upi_vpa", "last_payment_id"]
    readonly_fields = [
        "txnid", "va_id", "va_number", "va_ifsc", "upi_vpa", "qr_code_url",
        "order_id", "last_payment_id", "webhook_payload", "created_at", "updated_at",
    ]


@admin.register(NityaSevaMandate)
class NityaSevaMandateAdmin(NoBulkDeleteAdminMixin, admin.ModelAdmin):
    list_display    = ["txnid", "full_name", "mobile", "seva_type",
                       "amount", "mandate_status", "last_debit_status",
                       "total_debits_done", "wants_80g", "created_at"]
    list_filter     = ["mandate_status", "last_debit_status",
                       "seva_type", "wants_80g"]
    search_fields   = ["txnid", "full_name", "mobile",
                       "pan_number", "last_debit_pg_txnid"]
    readonly_fields = ["txnid", "access_key", "last_notification_id",
                       "last_notification_number", "last_debit_number",
                       "last_debit_pg_txnid", "mandate_webhook_payload",
                       "debit_webhook_payload", "created_at", "updated_at"]
