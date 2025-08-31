from django.conf import settings
from django.db import models


class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer")
    customer_id = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, unique=True, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.customer_id} - {self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        # Keep linked Django User in sync: username as customer_id, and basic fields
        if self.user:
            updated = False
            if self.user.username != self.customer_id:
                self.user.username = self.customer_id
                updated = True
            if self.user.first_name != self.first_name:
                self.user.first_name = self.first_name
                updated = True
            if self.user.last_name != self.last_name:
                self.user.last_name = self.last_name
                updated = True
            if self.user.email != self.email:
                self.user.email = self.email
                updated = True
            if updated:
                # Avoid recursion; save User directly
                self.user.save(update_fields=["username", "first_name", "last_name", "email"])
        super().save(*args, **kwargs)
