import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from datetime import timezone

from .integrations.hdfc import create_session, get_order_status, HdfcError, _sanitize_order_id
from .models import Order

def _json_body(request):
    try: return json.loads(request.body.decode("utf-8"))
    except Exception: return None

def hdfc_test_page_view(request):
    """Render a simple test page to initiate an HDFC payment session.

    Prefills customer info from the logged-in user's profile (Customer).
    """
    ctx = {}
    if request.user.is_authenticated:
        try:
            ctx["mobile"] = getattr(request.user.customer, "phone", "") or ""
        except Exception:
            ctx["mobile"] = ""
    return render(request, "payments/hdfc_test.html", ctx)

@csrf_exempt
@require_POST
def hdfc_create_session_view(request):
    body = _json_body(request)
    if not body:
        return HttpResponseBadRequest("Invalid JSON body")
    required = ["order_id", "amount", "customer_id", "customer_email", "customer_phone"]
    missing = [k for k in required if not body.get(k)]
    if missing:
        return HttpResponseBadRequest(f"Missing fields: {', '.join(missing)}")

    # Normalize order_id to match gateway and DB constraints (<=20 alnum)
    raw_oid = str(body.get("order_id", ""))
    oid = _sanitize_order_id(raw_oid)
    if not oid:
        return HttpResponseBadRequest("order_id must contain alphanumeric characters (max 20)")

    try:
        result = create_session(
            order_id=oid,
            amount=body["amount"],
            customer_id=body["customer_id"],
            customer_email=body["customer_email"],
            customer_phone=body["customer_phone"],
            first_name=body.get("first_name", ""),
            last_name=body.get("last_name", ""),
            description=body.get("description", ""),
            currency=body.get("currency", "INR"),
        )
        data = result["data"]
        bank_id = data.get("id") or ""
        links = data.get("payment_links", {}) or {}
        sdk = data.get("sdk_payload", None)

        Order.objects.update_or_create(
            order_id=oid,
            defaults={
                "bank_order_id": bank_id,
                "status": str(data.get("status", "NEW")),
                "amount": body["amount"],
                "currency": body.get("currency", "INR"),
                "customer_id": body["customer_id"],
                "customer_email": body["customer_email"],
                "customer_phone": body["customer_phone"],
                "payment_links_web": links.get("web", "") or links.get("mobile", "") or "",
                "sdk_payload": sdk,
                "metadata": {"payment_links": links},
            },
        )

        resp = JsonResponse(result, status=200, safe=False)
        resp.set_cookie("hdfc_last_order_id", oid, max_age=1800, secure=True, samesite="Lax")
        resp.set_cookie("hdfc_customer_id", body["customer_id"], max_age=1800, secure=True, samesite="Lax")
        return resp

    except HdfcError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400, safe=False)
    except Exception as e:
        # Ensure JSON error instead of HTML 500 page for the test client
        return JsonResponse({"ok": False, "error": f"Server error: {str(e)}"}, status=500, safe=False)

@require_GET
def hdfc_order_status_view(request, order_id: str):
    oid = _sanitize_order_id(order_id)
    customer_id = request.GET.get("customer_id", "")
    if not customer_id:
        return HttpResponseBadRequest("customer_id is required")

    try:
        result = get_order_status(oid, customer_id)
        data = result["data"]

        # persist
        try:
            order = Order.objects.get(order_id=oid)
        except Order.DoesNotExist:
            order = None

        if order:
            order.status = str(data.get("status", order.status or ""))
            order.bank_order_id = data.get("id", order.bank_order_id or "")
            order.txn_id = data.get("txn_id", order.txn_id or "")
            order.payment_method_type = data.get("payment_method_type", order.payment_method_type or "")
            order.payment_method = data.get("payment_method", order.payment_method or "")
            order.auth_type = data.get("auth_type", order.auth_type or "")
            order.refunded = bool(data.get("refunded", order.refunded))
            try:
                order.amount_refunded = data.get("amount_refunded", order.amount_refunded)
            except Exception:
                pass
            order.last_status_payload = data

            iso = data.get("order_expiry") or (data.get("metadata") or {}).get("order_expiry")
            if iso:
                dt = parse_datetime(iso)
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                order.order_expiry = dt

            order.save()

        result["is_paid"] = str(data.get("status", "")).upper() == "CHARGED"
        return JsonResponse(result, status=200, safe=False)

    except HdfcError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400, safe=False)

@csrf_exempt
def hdfc_return_view(request):
    order_id = request.POST.get("order_id") or request.GET.get("order_id") or ""
    customer_id = request.POST.get("customer_id") or request.GET.get("customer_id") or ""
    ctx = {"order_id": order_id, "customer_id": customer_id}
    resp = render(request, "payments/return.html", ctx)
    if order_id:
        resp.set_cookie("hdfc_last_order_id", order_id, max_age=1800, secure=True, samesite="Lax")
    if customer_id:
        resp.set_cookie("hdfc_customer_id", customer_id, max_age=1800, secure=True, samesite="Lax")
    return resp
