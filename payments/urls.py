from django.urls import path
from . import views

urlpatterns = [
    path("test", views.hdfc_test_page_view, name="hdfc_test"),
    path("create-session", views.hdfc_create_session_view, name="hdfc_create_session"),
    path("status/<str:order_id>", views.hdfc_order_status_view, name="hdfc_order_status"),
    path("return", views.hdfc_return_view, name="hdfc_return"),  # https://.../payments/return
]
