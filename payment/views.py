# payment/views.py
import uuid, decimal, requests
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
from django.conf import settings
from django.db import transaction
from .models import Order
from .utils import basic_auth_header, verify_hmac

SESSION_PATH = "/docs/api/session"  # <-- adjust to the exact session endpoint from your doc/sample
# (Docs call it “Create Session / Create Order to open payment page”)
# If your sample shows a different path (e.g. /api/v2/session or /session), replace it.

def _session_url():
    base = settings.HDFC_SMART["BASE_URL"].rstrip("/")
    return base + SESSION_PATH

def start_payment(request):
    # In real life, create Order via POST from your own checkout
    try:
        amount = decimal.Decimal(request.GET.get("amount", "2500.00"))
    except decimal.InvalidOperation:
        return HttpResponseBadRequest("Invalid amount")
    category = request.GET.get("category", "")
    order = Order.objects.create(
        order_id=uuid.uuid4().hex[:12].upper(),
        amount=amount,
        status="processing",
        category=category,
    )

    # Payload shape follows the SmartGateway “Session / Create Order” doc.
    # Confirm exact keys from your sample project page.
    payload = {
        "merchant_id": settings.HDFC_SMART["MERCHANT_ID"],
        "client_id": settings.HDFC_SMART["CLIENT_ID"],  # 'hdfcmaster' in UAT
        "order_id": order.order_id,
        "amount": str(order.amount),
        "currency": "INR",
        "customer": {
            "first_name": request.GET.get("name", "Guest"),
            "email": request.GET.get("email", "guest@example.com"),
            "phone_number": request.GET.get("phone", "9999999999"),
        },
        "return_url": settings.HDFC_SMART["RETURN_URL"],
    }

    headers = {
        "Authorization": basic_auth_header(),
        "Content-Type": "application/json",
    }
    r = requests.post(_session_url(), json=payload, headers=headers, timeout=20)
    data = r.json() if r.headers.get("content-type","").startswith("application/json") else {}

    # Adjust these keys per API response (docs say SDK payload + payment link)
    payment_link = data.get("payment_link") or data.get("payment_url") or data.get("redirect_url")
    order.gateway_order_id = data.get("order_id") or data.get("bank_order_id")
    order.raw_req, order.raw_resp = payload, data
    order.save(update_fields=["gateway_order_id","raw_req","raw_resp"])

    if not payment_link:
        return HttpResponseBadRequest("Could not create payment session")

    return redirect(payment_link)


@csrf_exempt
def hdfc_return(request):
    """
    SmartGateway will hit this URL after payment.
    Enable “Response HMAC signature” in dashboard and verify with RESPONSE_KEY.
    """
    data = request.POST.dict() or request.GET.dict()
    # Depending on configuration, the signature might arrive as 'signature' or 'hmac'.
    received_sig = data.get("signature") or data.get("hmac") or data.get("mac") or ""

    # Configure the exact fields list from your docs/sample kit:
    FIELDS_IN_MAC = ["merchant_id", "order_id", "amount", "status"]  # <- confirm exact order
    mac_payload = {k: data.get(k, "") for k in FIELDS_IN_MAC}

    valid = verify_hmac(mac_payload, received_sig, FIELDS_IN_MAC)

    order_id = data.get("order_id")
    if not order_id:
        return HttpResponseBadRequest("order_id missing")

    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(order_id=order_id)
            order.raw_resp = data
            order.gateway_txn_id = data.get("txn_id") or data.get("transaction_id")

            if not valid:
                order.status = "failed"
            else:
                status = (data.get("status") or "").upper()
                order.status = "paid" if status in ("SUCCESS","S","OK","CAPTURED") else "failed"

            order.save()
    except Order.DoesNotExist:
        return HttpResponseBadRequest("Unknown order_id")

    return redirect(f"/thank-you?order_id={order_id}") if order.status == "paid" \
           else redirect(f"/payment-error?order_id={order_id}")
