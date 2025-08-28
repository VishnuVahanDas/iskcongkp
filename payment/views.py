# payment/views.py
import uuid, decimal, requests, logging
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
from django.conf import settings
from django.db import transaction
from .models import Order
from .utils import jwt_auth_header, verify_hmac

logger = logging.getLogger(__name__)

SESSION_PATH = "/api/v1/session"  # <-- replace with the actual session endpoint from HDFC docs
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
        "client_id": settings.HDFC_SMART["PAYMENT_PAGE_CLIENT_ID"],  # 'hdfcmaster' in UAT
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
        "Authorization": jwt_auth_header(),
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(_session_url(), json=payload, headers=headers, timeout=20)
    except requests.RequestException:
        logger.exception(
            "HDFC session creation request failed for order_id=%s: payload=%s",
            order.order_id,
            payload,
        )
        return HttpResponseBadRequest(
            f"Could not create payment session. Reference ID: {order.order_id}"
        )

    if r.status_code != 200:
        logger.error(
            "HDFC session creation failed for order_id=%s: status=%s text=%s",
            order.order_id,
            r.status_code,
            r.text,
        )
        order.raw_req = payload
        order.raw_resp = {"status_code": r.status_code, "text": r.text}
        order.save(update_fields=["raw_req", "raw_resp"])
        return HttpResponseBadRequest(
            f"Could not create payment session. Reference ID: {order.order_id}"
        )

    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}

    # Extract redirect URL from nested data per HDFC API
    inner = data.get("data") or {}
    payment_link = inner.get("redirectUrl")
    order.gateway_order_id = inner.get("orderId") or data.get("order_id") or data.get("bank_order_id")
    order.raw_req, order.raw_resp = payload, data
    order.save(update_fields=["gateway_order_id", "raw_req", "raw_resp"])

    if not payment_link:
        msg = inner.get("message") or data.get("message") or "Redirect URL missing in response"
        logger.error(
            "HDFC response missing redirect URL for order_id=%s: payload=%s status=%s text=%s",
            order.order_id,
            payload,
            r.status_code,
            r.text,
        )
        return HttpResponseBadRequest(f"{msg}. Reference ID: {order.order_id}")

    return redirect(payment_link)


@csrf_exempt
def hdfc_return(request):
    """
    SmartGateway will hit this URL after payment.
    Enable “Response HMAC signature” in dashboard and verify with RESPONSE_KEY.
    """
    logger.debug("HDFC return POST data: %s", request.POST.dict())
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

    template = "donation/success.html" if order.status == "paid" else "donation/failure.html"
    return render(request, template, {"order": order})
