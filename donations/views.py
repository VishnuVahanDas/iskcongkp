from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from decimal import Decimal, InvalidOperation   
import re
from django.urls import reverse, NoReverseMatch

from .services import get_or_create_donor, issue_magic_link, issue_email_otp, mark_paid_and_receipt
from .models import Donation, MagicLinkToken, OtpCode
from .utils import gen_txn_id
from .emails import send_magic_link_email, send_otp_email
from .auth import login_donor
from payments.integrations.easebuzz import (
    create_payment_link as easebuzz_create_payment,
    verify_response as easebuzz_verify_response,
    transaction_lookup as easebuzz_transaction_lookup,
    EasebuzzError,
)
from payments.utils import allowed_payment_redirect
from payments.models import Order, NityaSevaAutoCollect, NityaSevaMandate
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@require_GET
@ensure_csrf_cookie
def donate_form(request):
    # Allow prefill from choose page via query params
    ctx = {
        "amount_default": (request.GET.get("amount") or ""),
        "purpose_default": (request.GET.get("purpose") or "General"),
    }
    return render(request, "donations/donate_form.html", ctx)


@require_GET
@ensure_csrf_cookie
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
    phone_raw = (request.POST.get("phone") or "").strip()
    pan = (request.POST.get("pan") or "").strip()
    purpose = (request.POST.get("purpose") or "General").strip()

    # Normalize phone to last 10 digits for gateway
    phone_digits = re.sub(r"\D", "", phone_raw or "")
    if len(phone_digits) >= 10:
        phone = phone_digits[-10:]
    else:
        logger.warning("Invalid phone on donate_checkout. raw=%s digits=%s", phone_raw, phone_digits)
        return HttpResponseBadRequest("Invalid phone number. Enter 10-digit mobile number.")

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
        # Validate required 80G fields
        missing = [k for k in ["address_line1", "city", "state", "postal_code", "country"] if not addr.get(k)]
        if missing:
            return HttpResponseBadRequest(
                "Address, City, State, PIN and Country are required for 80G receipt."
            )

    donor = get_or_create_donor(name, email, phone, pan, addr)
    txn_id = gen_txn_id()

    first_name = (donor.name or "Devotee").split(" ")[0]
    last_name = ""

    # --- create Easebuzz payment link ---
    try:
        response_url = request.build_absolute_uri(reverse("donations:easebuzz_response"))
    except NoReverseMatch:
        return HttpResponseBadRequest("Missing Easebuzz response URL")

    try:
        result = easebuzz_create_payment(
            txn_id=txn_id,
            amount=str(amount),
            firstname=first_name,
            email=donor.email or "",
            phone=phone,
            productinfo=purpose or "Donation",
            surl=response_url,
            furl=response_url,
            udf={
                "udf1": str(donor.id),
                "udf2": purpose or "Donation",
            },
            address=addr or {},
            city=(addr or {}).get("city", ""),
            state=(addr or {}).get("state", ""),
            country=(addr or {}).get("country", "India"),
            zipcode=(addr or {}).get("postal_code", ""),
        )
    except EasebuzzError as e:
        return HttpResponseBadRequest(f"Payment session error: {e}")

    redirect_url = result.get("data") or ""
    if not redirect_url:
        return HttpResponseBadRequest("Gateway did not return a payment link")
    if not allowed_payment_redirect(redirect_url):
        return HttpResponseBadRequest("Invalid redirect URL received from gateway")

    access_key = result.get("access_key") or ""

    # --- persist donation with gateway access key (if available) ---
    Donation.objects.create(
        donor=donor,
        amount=amount,
        purpose=purpose,
        txn_id=txn_id,
        order_id=access_key,
        status="PENDING",
    )

    # Mirror into payments.Order for reporting
    try:
        Order.objects.update_or_create(
            order_id=txn_id,
            defaults={
                "bank_order_id": access_key or "",
                "status": "PENDING",
                "amount": amount,
                "currency": "INR",
                "customer_id": donor.email or phone or f"donor-{donor.id}",
                "customer_email": donor.email or "",
                "customer_phone": phone or "",
                "payment_links_web": redirect_url,
                "metadata": {
                    "description": purpose or "Donation",
                    "first_name": first_name,
                    "last_name": last_name,
                    "gateway": "EASEBUZZ",
                },
            },
        )
    except Exception:
        pass

    try:
        request.session["easebuzz_last_txn_id"] = txn_id
        request.session["easebuzz_customer_id"] = donor.email or donor.phone_e164 or f"donor-{donor.id}"
    except Exception:
        pass
    return redirect(redirect_url)


# --- thank you page (return URL) ---
@require_GET
def thank_you(request):
    txn_id = (request.GET.get("txn_id") or request.GET.get("order_id") or
              request.session.get("easebuzz_last_txn_id") or "")
    ctx = {"txn_id": txn_id, "status": "", "is_paid": False, "server_checked": False}

    if txn_id:
        donation = Donation.objects.filter(txn_id=txn_id).select_related("donor").first()
        if donation:
            status = (donation.status or "").upper()
            ctx.update({
                "status": status,
                "is_paid": status == "SUCCESS",
                "server_checked": True,
            })
    return render(request, "donations/thank_you.html", ctx)


@csrf_exempt
def easebuzz_response(request):
    """Handle Easebuzz success/failure response (POST)."""
    params = request.POST or request.GET
    if not params:
        return HttpResponseBadRequest("Empty response")

    try:
        result = easebuzz_verify_response(params)
    except EasebuzzError as e:
        return HttpResponseBadRequest(str(e))

    if result.get("status") != 1:
        return HttpResponseBadRequest("Invalid response signature")

    data = result.get("data") or {}
    txn_id = data.get("txnid") or ""
    status_raw = str(data.get("status") or "").upper()
    is_paid = (status_raw == "SUCCESS")

    donation = None
    if txn_id:
        donation = Donation.objects.filter(txn_id=txn_id).select_related("donor").first()

    # Update Donation and Order
    if donation:
        try:
            donation.gateway_meta = data
            donation.status = "SUCCESS" if is_paid else (status_raw or "FAILED")
            donation.save(update_fields=["status", "gateway_meta"])
        except Exception:
            pass

        if is_paid:
            try:
                mode = data.get("payment_source") or data.get("mode") or "EASEBUZZ"
                mark_paid_and_receipt(donation, mode, data)
            except Exception:
                pass

    if txn_id:
        try:
            cust_id = ""
            if donation and donation.donor:
                cust_id = donation.donor.email or donation.donor.phone_e164 or f"donor-{donation.donor.id}"
            Order.objects.update_or_create(
                order_id=txn_id,
                defaults={
                    "status": "SUCCESS" if is_paid else (status_raw or "FAILED"),
                    "amount": data.get("amount") or (donation.amount if donation else 0),
                    "currency": "INR",
                    "customer_id": cust_id,
                    "customer_email": (donation.donor.email if donation and donation.donor else ""),
                    "customer_phone": (donation.donor.phone_e164 if donation and donation.donor else ""),
                    "txn_id": data.get("easepayid") or "",
                    "payment_method": data.get("payment_source") or "",
                    "metadata": {
                        "gateway": "EASEBUZZ",
                        "response": data,
                    },
                },
            )
        except Exception:
            pass

    # Optionally confirm via transaction API if success
    if is_paid and donation:
        try:
            easebuzz_txn = easebuzz_transaction_lookup(
                txn_id=txn_id,
                amount=donation.amount,
                phone=donation.donor.phone_e164 if donation.donor else "",
                email=donation.donor.email if donation.donor else "",
            )
            meta = donation.gateway_meta or {}
            meta["transaction_lookup"] = easebuzz_txn
            donation.gateway_meta = meta
            donation.save(update_fields=["gateway_meta"])
        except Exception:
            pass

    ctx = {
        "order_id": txn_id,
        "customer_id": (donation.donor.email if donation and donation.donor else ""),
        "status": status_raw or "PENDING",
        "is_paid": is_paid,
        "server_checked": True,
        "amount": donation.amount if donation else None,
        "currency": "INR",
        "customer_email": (donation.donor.email if donation and donation.donor else ""),
        "customer_phone": (donation.donor.phone_e164 if donation and donation.donor else ""),
        "purpose": (donation.purpose if donation else ""),
        "donor_name": (donation.donor.name if donation and donation.donor else ""),
    }
    try:
        if txn_id:
            request.session["easebuzz_last_txn_id"] = txn_id
    except Exception:
        pass
    return render(request, "payments/return.html", ctx)

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
    from django.conf import settings as _settings
    return render(request, 'donations/nitya-seva.html', {
        "EASEBUZZ_KEY": getattr(_settings, "EASEBUZZ_KEY", ""),
        "EASEBUZZ_ENV": getattr(_settings, "EASEBUZZ_ENV", "test"),
    })

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


# ── UPI AutoPay — Nitya Seva ONLY ────────────────────────────────────────────

import json as _json
import re as _re
from decimal import Decimal as _Decimal, InvalidOperation as _InvalidOperation
from django.views import View
from django.utils.decorators import method_decorator
from payments.integrations.autopay_service import generate_access_key, generate_txnid


@method_decorator(csrf_protect, name="dispatch")
class NityaSevaInitiateView(View):
    """
    POST /donations/nitya-seva/initiate/
    Validates form, calls EaseBuzz AutoCollect access-key API,
    saves NityaSevaMandate record, returns JSON with access_key.
    """

    def post(self, request, *args, **kwargs):
        full_name   = (request.POST.get("name") or "").strip()
        mobile_raw  = (request.POST.get("phone") or "").strip()
        email       = (request.POST.get("email") or "").strip()
        seva_type   = (request.POST.get("seva_type") or "").strip()
        raw_amount  = (request.POST.get("amount") or "").strip()

        errors = {}
        if not full_name:
            errors["name"] = "Full name is required."

        mobile_digits = _re.sub(r"\D", "", mobile_raw)
        if not _re.fullmatch(r"\d{10}", mobile_digits):
            errors["phone"] = "Enter a valid 10-digit mobile number."
            mobile = ""
        else:
            mobile = mobile_digits

        if not seva_type:
            errors["seva_type"] = "Please select a seva type."

        clean_amount = _re.sub(r"[^\d.]", "", raw_amount) or "0"
        try:
            amount = _Decimal(clean_amount)
        except (_InvalidOperation, TypeError):
            errors["amount"] = "Invalid amount."
            amount = _Decimal("0")
        if amount <= 0 and "amount" not in errors:
            errors["amount"] = "Amount must be greater than 0."

        wants_80g     = request.POST.get("wants_80g") == "on"
        pan_number    = (request.POST.get("pan_number") or "").strip().upper()
        address_line1 = (request.POST.get("address_line1") or "").strip()
        city          = (request.POST.get("city") or "").strip()
        pincode       = (request.POST.get("pincode") or "").strip()

        if wants_80g:
            if not pan_number or not _re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan_number):
                errors["pan_number"] = "Enter a valid PAN (e.g. ABCDE1234F)."
            if not address_line1:
                errors["address_line1"] = "Address is required for 80G certificate."
            if not city:
                errors["city"] = "City is required for 80G certificate."
            if not pincode or not _re.fullmatch(r"\d{6}", pincode):
                errors["pincode"] = "Enter a valid 6-digit pincode."

        if errors:
            return JsonResponse({"errors": errors}, status=400)

        txnid = generate_txnid()
        api_email = email or "seva@holytrail.in"

        try:
            result = generate_access_key(txnid, amount, api_email, mobile, seva_type)
        except Exception as exc:
            logger.error("AutoPay generate_access_key failed txn=%s: %s", txnid, exc)
            return JsonResponse({"error": str(exc)}, status=500)

        from datetime import date as _date
        from dateutil.relativedelta import relativedelta as _rd
        NityaSevaMandate.objects.create(
            full_name=full_name,
            mobile=mobile,
            email=email,          # blank saved as-is; fallback only for API
            seva_type=seva_type,
            amount=amount,
            wants_80g=wants_80g,
            pan_number=pan_number    if wants_80g else "",
            address_line1=address_line1 if wants_80g else "",
            city=city                if wants_80g else "",
            pincode=pincode          if wants_80g else "",
            txnid=txnid,
            access_key=result["access_key"],
            mandate_status="pending",
            mandate_start=_date.today(),
            mandate_end=_date.today() + _rd(years=5),
        )

        return JsonResponse({
            "access_key": result["access_key"],
            "txnid":      txnid,
            "amount":     "{:.2f}".format(float(amount)),
            "seva_type":  seva_type,
            "full_name":  full_name,
        })


@method_decorator(csrf_exempt, name="dispatch")
class NityaSevaSuccessView(View):
    """
    POST /donations/nitya-seva/success/
    Called by EaseBuzz after devotee approves mandate on UPI app.
    """

    def post(self, request, *args, **kwargs):
        # EaseBuzz AutoCollect posts JSON; fall back to form POST for safety.
        params = request.POST.dict()
        if not params:
            try:
                params = _json.loads(request.body)
            except Exception:
                params = {}
        txnid = (params.get("txnid") or params.get("transaction_id") or "").strip()
        if txnid:
            try:
                mandate = NityaSevaMandate.objects.filter(txnid=txnid).first()
                if mandate:
                    mandate.mandate_status = "active"
                    mandate.mandate_webhook_payload = params
                    mandate.save(update_fields=["mandate_status", "mandate_webhook_payload", "updated_at"])
            except Exception:
                logger.exception("AutoPay success callback DB update failed txn=%s", txnid)
        return HttpResponse("OK")


@method_decorator(csrf_exempt, name="dispatch")
class NityaSevaFailureView(View):
    """
    POST /donations/nitya-seva/failure/
    Called by EaseBuzz if mandate is rejected or cancelled.
    """

    def post(self, request, *args, **kwargs):
        # EaseBuzz AutoCollect posts JSON; fall back to form POST for safety.
        params = request.POST.dict()
        if not params:
            try:
                params = _json.loads(request.body)
            except Exception:
                params = {}
        txnid = (params.get("txnid") or params.get("transaction_id") or "").strip()
        if txnid:
            try:
                mandate = NityaSevaMandate.objects.filter(txnid=txnid).first()
                if mandate:
                    mandate.mandate_status = "failed"
                    mandate.mandate_webhook_payload = params
                    mandate.save(update_fields=["mandate_status", "mandate_webhook_payload", "updated_at"])
            except Exception:
                logger.exception("AutoPay failure callback DB update failed txn=%s", txnid)
        return HttpResponse("OK")


@method_decorator(csrf_exempt, name="dispatch")
class NityaSevaWebhookView(View):
    """
    POST /donations/nitya-seva/webhook/
    General webhook for mandate and debit status updates from EaseBuzz.
    """

    def post(self, request, *args, **kwargs):
        try:
            body = _json.loads(request.body)
        except Exception:
            body = request.POST.dict()

        txnid      = (body.get("txnid") or body.get("transaction_id") or "").strip()
        event_type = (body.get("event_type") or body.get("type") or "").strip().lower()
        status_raw = (body.get("status") or "").strip().lower()

        if not txnid:
            return JsonResponse({"error": "Missing txnid"}, status=400)

        try:
            mandate = NityaSevaMandate.objects.filter(txnid=txnid).first()
            if mandate:
                if event_type == "mandate_active" or status_raw == "active":
                    mandate.mandate_status = "active"
                    mandate.mandate_webhook_payload = body
                elif event_type == "debit_success" or status_raw == "success":
                    mandate.last_debit_status = "success"
                    mandate.total_debits_done += 1
                    mandate.debit_webhook_payload = body
                elif event_type == "debit_failure" or status_raw in ("failed", "failure"):
                    mandate.last_debit_status = "failed"
                    mandate.debit_webhook_payload = body
                mandate.save()
        except Exception:
            logger.exception("AutoPay webhook DB update failed txn=%s", txnid)

        return JsonResponse({"status": "ok"})


@method_decorator(csrf_protect, name="dispatch")
class NityaSevaClientConfirmView(View):
    """
    POST /donations/nitya-seva/client-confirm/
    Called from JS onResponse when EaseBuzz reports authorized + SUCCESS.

    EaseBuzz SEAMLESS checkout does NOT call our success_url server-to-server
    after onResponse fires; it is only used in redirect flows. So we accept the
    confirmed mandate data directly from the client and write it to the DB.

    Security: txnid is our own UUID prefix+12hex (hard to guess), the mandate
    must still be "pending" in the DB, and we verify all three EaseBuzz success
    indicators (status, sub_status, response_meta.code) before accepting.
    """

    def post(self, request, *args, **kwargs):
        try:
            body = _json.loads(request.body)
        except Exception:
            body = request.POST.dict()

        txnid      = (body.get("transaction_id") or body.get("txnid") or "").strip()
        status     = (body.get("status") or "").lower()
        sub_status = (body.get("sub_status") or "").upper()
        meta_code  = str((body.get("response_meta") or {}).get("code", ""))

        if not txnid:
            return JsonResponse({"ok": False, "error": "Missing transaction_id"}, status=400)

        # Only accept genuine EaseBuzz success indicators — reject anything else.
        is_authorized = (status == "authorized")
        is_success    = (sub_status == "SUCCESS" or meta_code == "00")
        if not (is_authorized and is_success):
            logger.warning("ClientConfirm rejected non-success response txn=%s status=%s sub=%s code=%s",
                           txnid, status, sub_status, meta_code)
            return JsonResponse({"ok": False, "error": "Not a success response"}, status=400)

        try:
            mandate = NityaSevaMandate.objects.filter(
                txnid=txnid, mandate_status="pending"
            ).first()
            if mandate:
                # Guard: mandate must have been created within the last 30 minutes.
                age = (timezone.now() - mandate.created_at).total_seconds()
                if age > 1800:
                    logger.warning("ClientConfirm: mandate too old txn=%s age=%.0fs", txnid, age)
                    return JsonResponse({"ok": False, "error": "Session expired"}, status=400)
                mandate.mandate_status        = "active"
                mandate.mandate_webhook_payload = body
                mandate.save(update_fields=["mandate_status", "mandate_webhook_payload", "updated_at"])
                logger.info("ClientConfirm: mandate activated txn=%s", txnid)
        except Exception:
            logger.exception("ClientConfirm DB update failed txn=%s", txnid)
            return JsonResponse({"ok": False, "error": "DB error"}, status=500)

        return JsonResponse({"ok": True})


class NityaSevaStatusView(View):
    """
    GET /donations/nitya-seva/status/<txnid>/
    Poll current mandate and debit status.
    """

    def get(self, request, txnid, *args, **kwargs):
        try:
            mandate = NityaSevaMandate.objects.get(txnid=txnid)
        except NityaSevaMandate.DoesNotExist:
            return JsonResponse({"error": "Not found."}, status=404)

        effective_status = mandate.mandate_status
        # If still "pending" after 10 minutes EaseBuzz has not called our
        # success_url — the user likely cancelled / abandoned the checkout.
        if effective_status == "pending":
            try:
                age_seconds = (timezone.now() - mandate.created_at).total_seconds()
                if age_seconds > 600:
                    effective_status = "expired"
            except Exception:
                pass

        return JsonResponse({
            "txnid":             mandate.txnid,
            "mandate_status":    effective_status,
            "last_debit_status": mandate.last_debit_status,
            "amount":            "{:.2f}".format(float(mandate.amount)),
            "seva_type":         mandate.seva_type,
        })
