from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from decimal import Decimal, InvalidOperation   
import re
from django.urls import reverse, NoReverseMatch
from django.conf import settings

from .services import get_or_create_donor, issue_magic_link, issue_email_otp
from .models import Donation, MagicLinkToken, OtpCode
from .utils import gen_txn_id
from .emails import send_magic_link_email, send_otp_email
from .auth import login_donor
from payments.integrations.hdfc import create_session as hdfc_create_session, HdfcError
from django.utils import timezone


@require_GET
def donate_form(request):
    # Allow prefill from choose page via query params
    ctx = {
        "amount_default": (request.GET.get("amount") or ""),
        "purpose_default": (request.GET.get("purpose") or "General"),
    }
    return render(request, "donations/donate_form.html", ctx)


@require_GET
def donate_choose(request):
    """Choose cause and preset amount before donor details."""
    causes = [
        ("General", "General Donation"),
        ("Shastra Daan", "Shastra Daan"),
        ("Annadana Seva", "Annadana Seva"),
        ("Nitya Seva", "Nitya Seva"),
        ("Temple Seva", "Temple Seva"),
        ("Janmashtami Seva", "Janmashtami Seva"),
        ("Tula Daan Utsav", "Tula Daan Utsav"),
    ]
    presets = [501, 1001, 5001, 11001]
    return render(request, "donations/donate_choose.html", {"causes": causes, "presets": presets})


@require_POST
@csrf_protect
def donate_checkout(request):
    # --- collect + basic validation ---
    name = (request.POST.get("name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    pan = (request.POST.get("pan") or "").strip()
    purpose = (request.POST.get("purpose") or "General").strip()

    raw_amount = (request.POST.get("amount") or "").strip()
    # remove anything that's not a digit or dot (₹, commas, spaces, etc.)
    clean_amount = re.sub(r"[^\d.]", "", raw_amount) or "0"

    try:
        amount = Decimal(clean_amount)
    except (InvalidOperation, TypeError):
        return HttpResponseBadRequest("Invalid amount")

    if amount <= 0:
        return HttpResponseBadRequest("Amount must be > 0")

    need_80g = request.POST.get("need_80g") == "on"
    addr = None
    if need_80g:
        addr = dict(
            address_line1=(request.POST.get("address_line1") or "").strip(),
            address_line2=(request.POST.get("address_line2") or "").strip(),
            city=(request.POST.get("city") or "").strip(),
            state=(request.POST.get("state") or "").strip(),
            postal_code=(request.POST.get("postal_code") or "").strip(),
            country=(request.POST.get("country") or "IN").strip(),
        )

    donor = get_or_create_donor(name, email, phone, pan, addr)
    txn_id = gen_txn_id()

    # --- create HDFC session using the tested integration ---
    # We use txn_id as our order_id (<=20 alnum already)
    first_name = (donor.name or "Devotee").split(" ")[0]
    last_name = ""
    try:
        result = hdfc_create_session(
            order_id=txn_id,
            amount=str(amount),
            customer_id=donor.email or donor.phone_e164 or f"donor-{donor.id}",
            customer_email=donor.email or "",
            customer_phone=donor.phone_e164 or "",
            first_name=first_name,
            last_name=last_name,
            description=purpose or "Donation",
            currency="INR",
        )
    except HdfcError as e:
        return HttpResponseBadRequest(f"Payment session error: {e}")

    data = result.get("data") or {}
    bank_id = data.get("id") or ""
    links = data.get("payment_links") or {}
    redirect_url = links.get("web") or links.get("mobile") or ""
    if not redirect_url:
        return HttpResponseBadRequest("Gateway did not return a payment link")

    # --- persist donation with real order id from gateway ---
    donation = Donation.objects.create(
        donor=donor,
        amount=amount,
        purpose=purpose,
        txn_id=txn_id,
        order_id=bank_id,   # <-- HDFC session/order id
        status="PENDING",
    )

    # --- send donor to HDFC hosted payment page ---
    return redirect(redirect_url)


# --- thank you page (return URL) ---
@require_GET
def thank_you(request):
    # DO NOT trust query status; show a friendly page.
    return render(request, "donations/thank_you.html")

# --- magic link request (post-payment or manual) ---
@require_POST
@csrf_protect
def magic_request(request):
    email = request.POST.get("email","").strip().lower()
    from .models import Donor
    donor = Donor.objects.filter(email_norm=email).first()
    if not donor:
        return HttpResponseBadRequest("Email not found")
    mlt = issue_magic_link(donor)
    link = request.build_absolute_uri(reverse("donations:magic_claim", kwargs={"token": mlt.token}))
    send_magic_link_email(donor, link)
    return HttpResponse("Magic link sent")

@require_GET
def magic_claim(request, token: str):
    try:
        mlt = MagicLinkToken.objects.select_related("donor").get(token=token)
    except MagicLinkToken.DoesNotExist:
        return HttpResponseBadRequest("Invalid link")
    if mlt.used or mlt.expires_at < timezone.now():
        return HttpResponseBadRequest("Link expired")
    mlt.used = True
    mlt.save(update_fields=["used"])
    login_donor(request, mlt.donor)
    return render(request, "donations/claim_success.html", {"donor": mlt.donor})

# --- OTP flow (email OTP a.k.a. "magic otp") ---
@require_POST
@csrf_protect
def otp_request(request):
    email = request.POST.get("email","").strip().lower()
    from .models import Donor
    donor = Donor.objects.filter(email_norm=email).first()
    if not donor:
        return HttpResponseBadRequest("Email not found")
    otp = issue_email_otp(donor)
    send_otp_email(donor, otp.code)
    return HttpResponse("OTP sent")

@require_POST
@csrf_protect
def otp_verify(request):
    email = request.POST.get("email","").strip().lower()
    code = request.POST.get("code","").strip()
    from django.utils import timezone
    from .models import Donor, OtpCode
    donor = Donor.objects.filter(email_norm=email).first()
    if not donor:
        return HttpResponseBadRequest("Email not found")

    otp = OtpCode.objects.filter(donor=donor, channel="email", consumed=False).order_by("-created_at").first()
    if not otp:
        return HttpResponseBadRequest("No active OTP")
    if otp.expires_at < timezone.now():
        return HttpResponseBadRequest("OTP expired")
    otp.attempts += 1
    if otp.code != code:
        otp.save(update_fields=["attempts"])
        return HttpResponseBadRequest("Invalid code")
    # success
    otp.consumed = True
    otp.save(update_fields=["consumed","attempts"])
    login_donor(request, donor)
    return HttpResponse("Logged in")

# Create your views here.
def shastra_daan(request):
    return render(request, 'donations/shastra-daan.html')

def temple_seva(request):
    return render(request, 'donations/temple-seva.html')

def annadana_seva(request):
    return render(request, 'donations/annadaan.html')

def nitya_seva(request):
    return render(request, 'donations/nitya-seva.html')

def janmashtami_seva(request):
    return render(request, 'donations/janmashtami.html')

def tula_daan(request):
    return render(request, 'donations/tula-daan.html')

def donate_brick(request):
    return render(request, 'donations/donate-brick.html')


# ----- Hybrid flow helpers -----
@require_GET
def donor_claim_redirect(request):
    token = (request.GET.get("token") or "").strip()
    if not token:
        return HttpResponseBadRequest("Missing token")
    return magic_claim(request, token)


@login_required
def donor_dashboard(request):
    """Simple donor dashboard: list your donations and receipts."""
    from .models import Donor
    u = request.user
    # Resolve donor by username heuristic used in ensure_user_for_donor
    donor = None
    username = (u.username or "").strip()
    if username:
        donor = Donor.objects.filter(email_norm=username).first() or \
                Donor.objects.filter(phone_e164=username).first()
        if donor is None and username.startswith("donor-"):
            try:
                pk = int(username.split("-",1)[1])
                donor = Donor.objects.filter(pk=pk).first()
            except Exception:
                donor = None
    if donor is None and u.email:
        donor = Donor.objects.filter(email_norm=u.email.lower()).first()
    if donor is None:
        return render(request, "donations/dashboard.html", {"donations": [], "donor": None})

    donations = donor.donations.order_by("-created_at").all()
    return render(request, "donations/dashboard.html", {"donations": donations, "donor": donor})
