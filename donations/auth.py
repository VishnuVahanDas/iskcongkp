from django.contrib.auth import login, get_user_model
from django.utils import timezone

User = get_user_model()

def ensure_user_for_donor(donor):
    """
    If you want a Django auth user to back dashboards.
    Username as donor email/phone; passwordless.
    """
    username = donor.email_norm or donor.phone_e164 or f"donor-{donor.pk}"
    user, _ = User.objects.get_or_create(username=username, defaults={
        "email": donor.email or "",
        "is_active": True,
    })
    return user

def login_donor(request, donor):
    user = ensure_user_for_donor(donor)
    login(request, user)  # session-based
    donor.is_claimed = True
    donor.save(update_fields=["is_claimed"])
