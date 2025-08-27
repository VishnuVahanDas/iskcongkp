from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponseBadRequest
from urllib.parse import urlencode

from .forms import DonationForm


def start_payment(request):
    """Wrapper view to redirect donation details to the payment app."""

    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request")

    form = DonationForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Invalid data")

    amount = form.cleaned_data.get("amount")
    name = form.cleaned_data.get("name", "")
    email = form.cleaned_data.get("email", "")
    phone = form.cleaned_data.get("phone", "")
    category = form.cleaned_data.get("category", "")
    params = urlencode(
        {
            "amount": amount,
            "name": name,
            "email": email,
            "phone": phone,
            "category": category,
        }
    )
    return redirect(f"{reverse('payment:hdfc_start')}?{params}")


def shastra_daan(request):
    return render(request, "donation/shastra-daan.html")


def temple_seva(request):
    return render(request, "donation/temple-seva.html")


def annadana_seva(request):
    return render(request, "donation/annadaan.html")


def nitya_seva(request):
    return render(request, "donation/nitya-seva.html")


def janmashtami_seva(request):
    return render(request, "donation/janmashtami.html")


def tula_daan(request):
    return render(request, "donation/tula-daan.html")


def donate_brick(request):
    return render(request, "donation/donate-brick.html")

