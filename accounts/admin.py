from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_id", "user", "first_name", "last_name", "email", "created_at")
    search_fields = ("customer_id", "user__username", "first_name", "last_name", "email")
    list_filter = ("created_at",)
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")

