from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts"

    def ready(self):
        try:
            from django.contrib import admin
            admin.site.site_header = "ISKCON Gorakhpur Admin Panel"
            admin.site.site_title = "ISKCON Gorakhpur Admin"
            admin.site.index_title = "Administration"
        except Exception:
            # Avoid startup issues if admin isn't loaded
            pass
