from django.shortcuts import render

# Create your views here.
# payments/views.py
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from .integrations.hdfc import create_session, get_order_status, HdfcError


@csrf_exempt
def hdfc_return_view(request):
    # Bank may POST or redirect via GET. Read both.
    order_id = request.POST.get("order_id") or request.GET.get("order_id") or ""
    customer_id = request.POST.get("customer_id") or request.GET.get("customer_id") or ""

    # (Optional) store short-lived cookies so the page can auto-check status
    resp = render(request, "payments/return.html", {"order_id": order_id, "customer_id": customer_id})
    if order_id:
        resp.set_cookie("hdfc_last_order_id", order_id, max_age=1800, secure=True, samesite="Lax")
    if customer_id:
        resp.set_cookie("hdfc_customer_id", customer_id, max_age=1800, secure=True, samesite="Lax")
    return resp

def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return None

@csrf_exempt  # if calling from your own backend/frontend with CSRF token, you can remove this
@require_POST
def hdfc_create_session_view(request):
    body = _json_body(request)
    if not body:
        return HttpResponseBadRequest("Invalid JSON body")

    required = ["order_id", "amount", "customer_id", "customer_email", "customer_phone"]
    missing = [k for k in required if not body.get(k)]
    if missing:
        return HttpResponseBadRequest(f"Missing fields: {', '.join(missing)}")

    try:
        result = create_session(
            order_id=body["order_id"],
            amount=body["amount"],
            customer_id=body["customer_id"],
            customer_email=body["customer_email"],
            customer_phone=body["customer_phone"],
            first_name=body.get("first_name", ""),
            last_name=body.get("last_name", ""),
            description=body.get("description", ""),
            currency=body.get("currency", "INR"),
        )
        # Store result["data"] in your DB if you maintain an Orders table.
        return JsonResponse(result, status=200, safe=False)
    except HdfcError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400, safe=False)

@require_GET
def hdfc_order_status_view(request, order_id: str):
    customer_id = request.GET.get("customer_id", "")  # you can fetch from DB by order_id instead
    if not customer_id:
        return HttpResponseBadRequest("customer_id is required (or fetch by order_id from DB)")

    try:
        result = get_order_status(order_id, customer_id)
        # Decide paid: status == "CHARGED"
        data = result["data"]
        is_paid = str(data.get("status", "")).upper() == "CHARGED"
        result["is_paid"] = is_paid
        return JsonResponse(result, status=200, safe=False)
    except HdfcError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400, safe=False)
