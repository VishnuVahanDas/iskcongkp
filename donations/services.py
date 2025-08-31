from django.db import transaction
from django.utils import timezone
from .models import Donor, Donation, Receipt, MagicLinkToken, OtpCode
from .utils import normalize_email, gen_receipt_number, token_32, gen_otp, expiry

def normalize_phone(phone: str | None) -> str | None:
    return phone.strip() if phone else None  # TODO: use phonenumbers to format E.164

@transaction.atomic
def get_or_create_donor(name: str, email: str | None, phone: str | None, pan: str | None, addr: dict | None = None) -> Donor:
    email_norm = normalize_email(email)
    phone_e164 = normalize_phone(phone)
    pan_norm = (pan or "").strip().upper()

    donor = None
    if email_norm:
        donor = Donor.objects.select_for_update().filter(email_norm=email_norm).first()
    if donor is None and phone_e164:
        donor = Donor.objects.select_for_update().filter(phone_e164=phone_e164).first()
    if donor is None and pan_norm:
        donor = Donor.objects.select_for_update().filter(pan=pan_norm).first()

    if donor is None:
        donor = Donor.objects.create(
            email=email, email_norm=email_norm, phone_e164=phone_e164,
            name=name or "", pan=pan_norm,
            **(addr or {})
        )
    else:
        changed = False
        if not donor.email and email:
            donor.email = email; changed = True
        if email_norm and donor.email_norm != email_norm:
            donor.email_norm = email_norm; changed = True
        if not donor.phone_e164 and phone_e164:
            donor.phone_e164 = phone_e164; changed = True
        if not donor.pan and pan_norm:
            donor.pan = pan_norm; changed = True
        if name and (not donor.name or len(name) < len(name)):
            donor.name = name; changed = True
        if addr:
            for f,v in addr.items():
                if v and not getattr(donor, f):
                    setattr(donor, f, v); changed = True
        if changed:
            donor.save()
    return donor

@transaction.atomic
def issue_magic_link(donor: Donor, minutes=30) -> MagicLinkToken:
    mlt = MagicLinkToken.objects.create(
        donor=donor, token=token_32(), expires_at=expiry(minutes)
    )
    return mlt

@transaction.atomic
def issue_email_otp(donor: Donor, minutes=10) -> OtpCode:
    otp = OtpCode.objects.create(
        donor=donor, channel="email", code=gen_otp(), expires_at=expiry(minutes)
    )
    return otp

@transaction.atomic
def mark_paid_and_receipt(donation: Donation, mode: str, gateway_meta: dict) -> Receipt:
    if donation.status == "SUCCESS":
        return donation.receipt  # idempotent
    donation.status = "SUCCESS"
    donation.mode = mode
    donation.paid_at = timezone.now()
    donation.gateway_meta = gateway_meta or {}
    if not donation.issued_receipt_no:
        donation.issued_receipt_no = gen_receipt_number()
    donation.save()

    if not hasattr(donation, "receipt"):
        r = Receipt.objects.create(donation=donation, number=donation.issued_receipt_no)
        return r
    return donation.receipt
