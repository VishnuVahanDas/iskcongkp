from django.conf import settings
from django.shortcuts import render, redirect
from .forms import DonationForm
from payments.hdfc import encrypt

# Create your views here.

def pay(request):
    if request.method == "POST":
        form = DonationForm(request.POST)
        if form.is_valid():
            order_id = form.cleaned_data["order_id"]
            amount = form.cleaned_data["amount"]
            params = {
                "merchant_id": settings.HDFC_MERCHANT_ID,
                "order_id": order_id,
                "currency": "INR",
                "amount": f"{amount:.2f}",
                "redirect_url": request.build_absolute_uri("callback/"),
                "cancel_url": request.build_absolute_uri("callback/"),
                "language": "EN",
            }
            query = "&".join(f"{k}={v}" for k, v in params.items())
            enc_request = encrypt(query)
            context = {
                "enc_request": enc_request,
                "access_code": settings.HDFC_ACCESS_CODE,
                "payment_url": settings.HDFC_PAYMENT_URL,
            }
            return render(request, "donation/redirect.html", context)
    else:
        form = DonationForm()
    return render(request, "donation/pay.html", {"form": form})


def shastra_daan(request):
    return render(request, 'donation/shastra-daan.html')


def temple_seva(request):
    return render(request, 'donation/temple-seva.html')


def annadana_seva(request):
    return render(request, 'donation/annadaan.html')


def nitya_seva(request):
    return render(request, 'donation/nitya-seva.html')


def janmashtami_seva(request):
    return render(request, 'donation/janmashtami.html')


def tula_daan(request):
    return render(request, 'donation/tula-daan.html')


def donate_brick(request):
    return render(request, 'donation/donate-brick.html')
