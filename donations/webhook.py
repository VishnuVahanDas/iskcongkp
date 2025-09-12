import base64, json
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Order
from payments.utils import extract_payment_status

from .models import Donation
from .services import mark_paid_and_receipt, issue_magic_link


def _check_basic_auth(request) -> bool:
    user = getattr(settings, "HDFC_WEBHOOK_BASIC_USER", None)
    pwd  = getattr(settings, "HDFC_WEBHOOK_BASIC_PASS", "")
    if not user:
        return False
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        raw = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
        username, _, password = raw.partition(":")
    except Exception:
        return False
    return (username == user) and (password == pwd)


def _check_basic_auth_with_merchant_keys(request) -> bool:
    """Allow verifying webhook using Merchant ID and API Key as Basic auth.

    This lets you avoid configuring a separate webhook username/password in the dashboard.
    Configure SmartGateway to send username = HDFC_MERCHANT_ID and password = HDFC_API_KEY.
    """
    mid = getattr(settings, "HDFC_MERCHANT_ID", None)
    api_key = getattr(settings, "HDFC_API_KEY", None)
    if not (mid and api_key):
        return False
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        raw = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
        username, _, password = raw.partition(":")
    except Exception:
        return False
    return (username == mid) and (password == api_key)


def _check_custom_header(request) -> bool:
    key = getattr(settings, "HDFC_WEBHOOK_HEADER_KEY", None)
    val = getattr(settings, "HDFC_WEBHOOK_HEADER_VALUE", None)
    if not key or not val:
        return False
    return request.headers.get(key) == val


@csrf_exempt
def hdfc_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    # 🔐 Auth: enforce Basic auth either via explicit webhook creds OR MerchantID/API Key, optional extra custom header
    basic_ok = _check_basic_auth(request) or _check_basic_auth_with_merchant_keys(request)
    header_ok = _check_custom_header(request)
    creds_configured = any([
        getattr(settings, "HDFC_WEBHOOK_BASIC_USER", None),
        getattr(settings, "HDFC_MERCHANT_ID", None),
        getattr(settings, "HDFC_WEBHOOK_HEADER_KEY", None),
    ])
    if creds_configured and not (basic_ok or header_ok):
        return HttpResponse("Unauthorized", status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    # Map fields according to HDFC webhook samples (see docs)
    # Note: HDFC typically sends both a gateway order ID and a transaction ID.
    # In our flow, we pass our internal txn_id as the gateway "order_id" when creating the session.
    gw_order_id = payload.get("order", {}).get("id") or payload.get("order_id") or ""
    gw_txn_id   = payload.get("transaction", {}).get("id") or payload.get("txn_id") or ""

    norm_status, category, src = extract_payment_status(payload)
    mode = payload.get("payment", {}).get("method", "") or (payload.get("payment_method") or "")

    # Resolve donation robustly:
    # 1) If gateway sent back our order_id (which we set to our txn_id), match on Donation.txn_id == gw_order_id
    # 2) Else, if we stored the gateway order/session id on Donation.order_id, match on that
    # 3) Else, try matching on the gateway transaction id to Donation.txn_id
    #    or Donation.order_id (legacy/alternate maps)
    donation = None
    if gw_order_id:
        donation = Donation.objects.filter(txn_id=gw_order_id).first() or \
                   Donation.objects.filter(order_id=gw_order_id).first()
    if donation is None and gw_txn_id:
        donation = Donation.objects.filter(txn_id=gw_txn_id).first() or \
                   Donation.objects.filter(order_id=gw_txn_id).first()
    if donation is None:
        return HttpResponse("unknown order", status=202)

    if category == "success":
        receipt = mark_paid_and_receipt(donation, mode, payload)
        try:
            donation.status = norm_status
            donation.save(update_fields=["status"])
        except Exception:
            pass
        try:
            Order.objects.filter(order_id=gw_order_id).update(status=norm_status)
            if donation.order_id:
                Order.objects.filter(bank_order_id=donation.order_id).update(status=norm_status)
        except Exception:
            pass
        # send receipt + magic link unless already sent via another path
        meta = donation.gateway_meta or {}
        if not bool(meta.get("receipt_email_sent")):
            mlt = issue_magic_link(donation.donor)
            link = request.build_absolute_uri(
                reverse("donations:magic_claim", kwargs={"token": mlt.token})
            )
            from .emails import send_receipt_email
            send_receipt_email(donation, magic_link_url=link)
            meta["receipt_email_sent"] = True
            donation.gateway_meta = meta
            donation.save(update_fields=["gateway_meta"])
    elif category == "failed":
        donation.status = norm_status or "FAILED"
        donation.gateway_meta = payload
        donation.save(update_fields=["status", "gateway_meta"])
        try:
            Order.objects.filter(order_id=gw_order_id).update(status=norm_status)
            if donation.order_id:
                Order.objects.filter(bank_order_id=donation.order_id).update(status=norm_status)
        except Exception:
            pass
    elif category == "pending":
        donation.status = norm_status or donation.status
        donation.gateway_meta = payload
        donation.save(update_fields=["status", "gateway_meta"])
        try:
            Order.objects.filter(order_id=gw_order_id).update(status=norm_status)
            if donation.order_id:
                Order.objects.filter(bank_order_id=donation.order_id).update(status=norm_status)
        except Exception:
            pass
        return HttpResponse("ok", status=202)
    else:
        return HttpResponse("ok", status=202)

    return HttpResponse("ok")
