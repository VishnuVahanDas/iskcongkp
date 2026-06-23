from django.urls import path
from . import views

app_name = "payments"
urlpatterns = [
    path("easebuzz/initiate", views.easebuzz_initiate_view, name="easebuzz_initiate"),
    path("easebuzz/response", views.easebuzz_response_view, name="easebuzz_response"),
    path("my", views.my_payments_view, name="my_payments"),
]
