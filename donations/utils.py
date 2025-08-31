import secrets, string, datetime
from django.utils import timezone

def normalize_email(email: str | None) -> str | None:
    return email.strip().lower() if email else None

def token_32():
    return secrets.token_urlsafe(32)

def gen_receipt_number():
    # e.g., ISK-GKP-YYMM-XXXX
    now = timezone.now()
    return f"ISK-GKP-{now.strftime('%y%m')}-{secrets.randbelow(10_000):04d}"

def gen_txn_id():
    return f"DGKP{timezone.now().strftime('%m%d%H%M%S')}{secrets.randbelow(1000):03d}"

def gen_otp(n=6):
    return ''.join(secrets.choice(string.digits) for _ in range(n))

def expiry(minutes=15):
    return timezone.now() + datetime.timedelta(minutes=minutes)
