# payments/views.py
import json, uuid, logging
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from .hdfc_client import create_session, order_status, refund_order, decrypt_and_verify_hdfc_response

logger = logging.getLogger(__name__)

@csrf_exempt
def start_checkout(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    amount = body.get("amount")
    if not amount:
        return JsonResponse({"error": "amount is required"}, status=400)

    order_id = body.get("order_id") or uuid.uuid4().hex
    customer_id = body.get("customer_id", "guest")

    sg_payload = {
        "merchant_id": settings.HDFC_MERCHANT_ID,
        "order_id": order_id,
        "amount": f"{Decimal(str(amount)):.2f}",
        "currency": "INR",
        "customer": {
            "id": customer_id,
            "email": body.get("email", "test@example.com"),
            "mobile": body.get("mobile", "9999999999"),
        },
        "redirect_url": body.get("return_url") or settings.HDFC_RETURN_URL,
        "webhook_url": body.get("webhook_url") or settings.HDFC_WEBHOOK_URL,
    }

    try:
        sg_resp = create_session(sg_payload)
    except Exception as e:
        logger.exception("Failed to create session")
        # Try to surface gateway error body if available
        if getattr(e, "response", None) is not None:
            try:
                err_body = e.response.json()
            except Exception:
                err_body = getattr(e.response, "text", "")
            return JsonResponse({"error": "Failed to create session", "details": str(e), "response": err_body}, status=500)
        return JsonResponse({"error": "Failed to create session", "details": str(e)}, status=500)

    redirect_url = sg_resp.get("payment_link") or sg_resp.get("redirect_url") or sg_resp.get("url")
    if not redirect_url:
        return JsonResponse({"error": "No redirect URL returned", "response": sg_resp}, status=500)

    return JsonResponse({"order_id": order_id, "redirect_url": redirect_url, "raw": sg_resp})

def check_status(request, order_id):
    try:
        data = order_status(order_id)
    except Exception as e:
        return JsonResponse({"error": "Failed to fetch status", "details": str(e)}, status=500)
    return JsonResponse(data)

@csrf_exempt
def refund_view(request, order_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}
    refund_amount = body.get("amount")
    payload = {"amount": f"{Decimal(str(refund_amount)):.2f}"} if refund_amount else {}
    try:
        resp = refund_order(order_id, payload)
    except Exception as e:
        return JsonResponse({"error": "Failed to refund", "details": str(e)}, status=500)
    return JsonResponse(resp)

@csrf_exempt
def hdfc_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    # Decrypt+verify if encrypted structure
    if all(k in body for k in ("header", "encryptedKey", "iv", "encryptedPayload", "tag")):
        try:
            payload = decrypt_and_verify_hdfc_response(body)
        except Exception as e:
            return HttpResponseBadRequest(f"Decrypt/verify failed: {e}")
    else:
        payload = body

    # TODO: your DB update using 'payload'
    # Example:
    # order_id = payload.get("order_id")
    # status = payload.get("status")
    # amount = payload.get("amount")
    # verify = order_status(order_id)  # optional reconciliation

    return HttpResponse(status=200)

@ensure_csrf_cookie
def hdfc_test_console(request):
    return render(request, "payments/hdfc_test.html")
