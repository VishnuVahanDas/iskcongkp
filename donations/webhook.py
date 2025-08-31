import base64, json
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Donation
from .services import mark_paid_and_receipt, issue_magic_link
from django.urls import reverse

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

    # 🔐 Auth: if any auth method is configured, enforce it; otherwise accept (for environments without webhook auth)
    has_basic_cfg = bool(getattr(settings, "HDFC_WEBHOOK_BASIC_USER", None))
    has_hdr_cfg = bool(getattr(settings, "HDFC_WEBHOOK_HEADER_KEY", None)) and bool(getattr(settings, "HDFC_WEBHOOK_HEADER_VALUE", None))
    if has_basic_cfg or has_hdr_cfg:
        if not (_check_basic_auth(request) or _check_custom_header(request)):
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
    # Normalize status from multiple possible keys
    status      = str(
        payload.get("status") or
        (payload.get("order") or {}).get("status") or
        (payload.get("payment") or {}).get("status") or
        (payload.get("transaction") or {}).get("status") or
        (payload.get("result") or {}).get("status") or
        ""
    ).upper()
    mode        = payload.get("payment", {}).get("method", "") or (payload.get("payment_method") or "")

    # Resolve donation robustly:
    # 1) If gateway sent back our order_id (which we set to our txn_id), match on Donation.txn_id == gw_order_id
    # 2) Else, if we stored the gateway order/session id on Donation.order_id, match on that
    # 3) Else, try matching on the gateway transaction id to Donation.txn_id (legacy/alternate maps)
    donation = None
    if gw_order_id:
        donation = Donation.objects.filter(txn_id=gw_order_id).first() or \
                   Donation.objects.filter(order_id=gw_order_id).first()
    if donation is None and gw_txn_id:
        donation = Donation.objects.filter(txn_id=gw_txn_id).first()
    if donation is None:
        return HttpResponse("unknown order", status=202)

    # Treat common success statuses from gateway as paid
    success_statuses = {"SUCCESS", "SUCCESSFUL", "CHARGED", "PAID", "CAPTURED", "COMPLETED", "SETTLED"}
    if status in success_statuses:
        receipt = mark_paid_and_receipt(donation, mode, payload)
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
    elif status == "FAILED":
        donation.status = "FAILED"
        donation.gateway_meta = payload
        donation.save(update_fields=["status", "gateway_meta"])
    else:
        # Unknown/processing -> ack without state change
        return HttpResponse("ok", status=202)

    return HttpResponse("ok")
