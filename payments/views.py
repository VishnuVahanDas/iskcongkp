import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.db.models import Q

from .integrations.easebuzz import initiate_payment, parse_gateway_response, EasebuzzIntegrationError
from .models import Order
from .utils import generate_order_id


def _json_body(request):
    try: return json.loads(request.body.decode("utf-8"))
    except Exception: return None


@csrf_protect
@login_required
@require_POST
def easebuzz_initiate_view(request):
    body = _json_body(request)
    if not body:
        return HttpResponseBadRequest("Invalid JSON body")

    required = ["firstname", "phone", "email", "amount", "productinfo"]
    missing = [k for k in required if not body.get(k)]
    if missing:
        return HttpResponseBadRequest(f"Missing fields: {', '.join(missing)}")

    txnid = str(body.get("txnid") or generate_order_id(prefix="EZB"))
    response_url = request.build_absolute_uri(reverse("payments:easebuzz_response"))

    post_data = {
        "txnid": txnid,
        "firstname": body["firstname"],
        "phone": body["phone"],
        "email": body["email"],
        "amount": str(body["amount"]),
        "productinfo": body["productinfo"],
        "surl": body.get("surl") or response_url,
        "furl": body.get("furl") or response_url,
        "city": body.get("city", ""),
        "zipcode": body.get("zipcode", ""),
        "address2": body.get("address2", ""),
        "state": body.get("state", ""),
        "address1": body.get("address1", ""),
        "country": body.get("country", ""),
        "udf1": body.get("udf1", ""),
        "udf2": body.get("udf2", ""),
        "udf3": body.get("udf3", ""),
        "udf4": body.get("udf4", ""),
        "udf5": body.get("udf5", ""),
    }

    try:
        result = initiate_payment(post_data)
    except EasebuzzIntegrationError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Easebuzz request failed: {str(e)}"}, status=500)

    status = result.get("status")
    payment_url = result.get("data")
    if status == 1 and payment_url:
        return JsonResponse({"ok": True, "txnid": txnid, "payment_url": payment_url, "result": result})
    return JsonResponse({"ok": False, "txnid": txnid, "result": result}, status=400)


@csrf_exempt
@require_POST
def easebuzz_response_view(request):
    try:
        final_response = parse_gateway_response(request.POST)
        return JsonResponse({"ok": True, "response_data": final_response})
    except EasebuzzIntegrationError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Could not parse Easebuzz response: {str(e)}"}, status=500)


@login_required
def my_payments_view(request):
    """List previous payments for the logged-in customer."""
    cust_id = getattr(getattr(request.user, "customer", None), "customer_id", None) or request.user.username
    identifiers = set()
    if cust_id:
        identifiers.add(cust_id)
    if getattr(request.user, "email", None):
        identifiers.add(request.user.email)
    if getattr(request.user, "username", None):
        identifiers.add(request.user.username)

    try:
        from donations.models import Donor
        donor = None
        if request.user.email:
            donor = Donor.objects.filter(email_norm=request.user.email.lower()).first()
        if donor is None and request.user.username:
            donor = Donor.objects.filter(email_norm=request.user.username.lower()).first() or \
                    Donor.objects.filter(phone_e164=request.user.username).first()
        if donor:
            if donor.email:
                identifiers.add(donor.email)
            if donor.email_norm:
                identifiers.add(donor.email_norm)
            if donor.phone_e164:
                identifiers.add(donor.phone_e164)
    except Exception:
        donor = None

    q = Q()
    for ident in identifiers:
        if not ident:
            continue
        q |= Q(customer_id=ident) | Q(customer_email=ident) | Q(customer_phone=ident)
    if q:
        qs = Order.objects.filter(q).order_by("-created_at")
    else:
        qs = Order.objects.none()

    try:
        page = int(request.GET.get("page", "1"))
        if page < 1: page = 1
    except Exception:
        page = 1
    page_size = 10
    start = (page - 1) * page_size
    end = start + page_size
    total = qs.count()
    items = list(qs[start:end])
    has_next = end < total
    has_prev = start > 0

    ctx = {
        "orders": items,
        "page": page,
        "has_next": has_next,
        "has_prev": has_prev,
        "next_page": page + 1,
        "prev_page": page - 1,
        "customer_id": cust_id,
    }
    return render(request, "payments/my_payments.html", ctx)
