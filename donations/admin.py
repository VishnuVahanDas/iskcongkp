from django.contrib import admin
from .models import Donor, Donation, Receipt, MagicLinkToken, OtpCode


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


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ("id","name","email_norm","phone_e164","pan","is_claimed","created_at")
    search_fields = ("name","email","email_norm","phone_e164","pan")


@admin.register(Donation)
class DonationAdmin(NoBulkDeleteAdminMixin, admin.ModelAdmin):
    pass


@admin.register(Receipt)
class ReceiptAdmin(NoBulkDeleteAdminMixin, admin.ModelAdmin):
    pass


admin.site.register(MagicLinkToken)
admin.site.register(OtpCode)
