import json
from django.http import HttpResponse, HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Order
from payments.utils import extract_payment_status

from .models import Donation
from .services import mark_paid_and_receipt, issue_magic_link


@csrf_exempt
def payment_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    # Map fields from gateway webhook payload
    gw_order_id = payload.get("order", {}).get("id") or payload.get("order_id") or ""
    gw_txn_id   = payload.get("transaction", {}).get("id") or payload.get("txn_id") or ""

    norm_status, category, src = extract_payment_status(payload)
    mode = payload.get("payment", {}).get("method", "") or (payload.get("payment_method") or "")

    # Resolve donation:
    # 1) Match on Donation.txn_id == gw_order_id (our internal txn id passed as gateway order_id)
    # 2) Match on Donation.order_id == gw_order_id (gateway session/access key stored on donation)
    # 3) Fallback to gateway transaction id
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
