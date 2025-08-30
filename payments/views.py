from django.shortcuts import render

# Create your views here.
import uuid, hmac, hashlib, json, logging
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect

import requests
from .hdfc_client import create_session, order_status, refund_order
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from decimal import Decimal

logger = logging.getLogger(__name__)

@csrf_exempt
def start_checkout(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body or "{}")
    except:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    amount = body.get("amount")
    if not amount:
        return JsonResponse({"error": "amount is required"}, status=400)

    order_id = body.get("order_id") or uuid.uuid4().hex
    customer_id = body.get("customer_id", "guest")

    sg_payload = {
        "merchant_id": settings.HDFC_MERCHANT_ID,   # "SG3418"
        "order_id": order_id,
        "amount": f"{Decimal(amount):.2f}",         # e.g. "199.00"
        "currency": "INR",
        "customer": {
            "id": customer_id,
            "email": body.get("email", "test@example.com"),
            "mobile": body.get("mobile", "9999999999"),
        },
        "redirect_url": body.get("return_url") or "https://iskcongorakhpur.com/payments/return/",
        "webhook_url": body.get("webhook_url") or "https://iskcongorakhpur.com/payments/hdfc/webhook/",
    }

    try:
        sg_resp = create_session(sg_payload)
    except requests.exceptions.HTTPError as e:
        try:
            err_body = e.response.json()
        except ValueError:
            err_body = e.response.text
        logger.error(
            "create_session HTTPError: status=%s headers=%s payload=%s response=%s",
            getattr(e.response, "status_code", None),
            getattr(e.response, "headers", {}),
            sg_payload,
            err_body,
        )
        return JsonResponse(
            {
                "error": "Failed to create session",
                "details": str(e),
                "response": err_body,
            },
            status=500,
        )
    except Exception as e:
        logger.exception("Failed to create session")
        return JsonResponse({"error": "Failed to create session", "details": str(e)}, status=500)

    redirect_url = sg_resp.get("payment_link") or sg_resp.get("redirect_url") or sg_resp.get("url")
    if not redirect_url:
        return JsonResponse({"error": "No redirect URL returned", "response": sg_resp}, status=500)

    return JsonResponse({
        "order_id": order_id,
        "redirect_url": redirect_url,
        "raw": sg_resp
    })

@csrf_exempt
def hdfc_webhook(request):
    """
    Webhook endpoint to capture payment result.
    Ensure this URL is HTTPS, publicly accessible.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    raw = request.body
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        payload = {}

    # (Optional) Verify authenticity. Docs emphasize using HTTPS; if bank provides signature headers, verify them here.
    # Example: your own HMAC check if you configured a shared secret with your infra (not bank-provided):
    # sig_header = request.headers.get("X-Your-HMAC")
    # expected = hmac.new(settings.HDFC_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    # if not hmac.compare_digest(sig_header or "", expected):
    #     return HttpResponse("bad signature", status=400)

    # Update your order by payload["order_id"], payload["status"] etc.
    # Common statuses: CHARGED/SUCCESS, PENDING, FAILED, etc. (check your response payload contract)
    # Save full payload for audit.
    # Example pseudo:
    # order = Order.objects.get(order_id=payload["order_id"])
    # order.status = payload["status"]
    # order.gateway_response = payload
    # order.save()

    return HttpResponse(status=200)

def check_status(request, order_id):
    """
    Manual status poll / reconciliation (server-to-server).
    """
    data = order_status(order_id)
    # Update local order state if needed
    return JsonResponse(data)

@csrf_exempt
def refund_view(request, order_id):
    """
    Initiate refund for a CHARGED order.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    body = json.loads(request.body or "{}")
    refund_amount = body.get("amount")  # optional (full vs partial)
    payload = {"amount": refund_amount} if refund_amount else {}
    resp = refund_order(order_id, payload)
    return JsonResponse(resp)

@ensure_csrf_cookie
def hdfc_test_console(request):
    return render(request, "payments/hdfc_test.html")
