from django.urls import path

from . import views

app_name = "festivals"
urlpatterns = [
    path("vaishnava-calender", views.calender, name="calender"),
    path("festivals", views.festivals, name="festivals"),

]
