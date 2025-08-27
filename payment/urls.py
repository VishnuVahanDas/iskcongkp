# payment/urls.py
from django.urls import path
from .views import start_payment, hdfc_return

urlpatterns = [
    path("hdfc/start/", start_payment, name="hdfc_start"),
    path("hdfc/return/", hdfc_return, name="hdfc_return"),
]
