from django.contrib import admin
from .models import Donor, Donation, Receipt, MagicLinkToken, OtpCode

@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ("id","name","email_norm","phone_e164","pan","is_claimed","created_at")
    search_fields = ("name","email","email_norm","phone_e164","pan")

admin.site.register(Donation)
admin.site.register(Receipt)
admin.site.register(MagicLinkToken)
admin.site.register(OtpCode)
