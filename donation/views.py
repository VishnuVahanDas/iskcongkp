from django.shortcuts import render, redirect
from django.urls import reverse
from urllib.parse import urlencode

from .forms import DonationForm


def start_donation_payment(request):
    if request.method == "POST":
        form = DonationForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data.get("amount")
            name = request.POST.get("name", "")
            email = request.POST.get("email", "")
            phone = request.POST.get("phone", "")
            params = urlencode(
                {
                    "amount": amount,
                    "name": name,
                    "email": email,
                    "phone": phone,
                }
            )
            return redirect(f"{reverse('payment:hdfc_start')}?{params}")
    else:
        form = DonationForm()
    return render(request, "donation/pay.html", {"form": form})


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

