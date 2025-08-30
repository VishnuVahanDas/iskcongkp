# payments/urls.py
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("hdfc/test/", views.hdfc_test_console, name="hdfc_test"),
    path("hdfc/start/", views.start_checkout, name="hdfc_start"),
    path("hdfc/status/<str:order_id>/", views.check_status, name="hdfc_status"),
    path("hdfc/refund/<str:order_id>/", views.refund_view, name="hdfc_refund"),
    path("hdfc/webhook/", views.hdfc_webhook, name="hdfc_webhook"),
]
