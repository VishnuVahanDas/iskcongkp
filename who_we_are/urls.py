from django.urls import path

from . import views

app_name = "who_we_are"
urlpatterns = [
    path("about-us", views.about, name="about"),
    path("our-mission", views.our_mission, name="our_mission"),
    path("founder-acharya", views.founder_acharya, name="founder-acharya"),
    path("our-history", views.history, name="history"),
    path("our-philosophy", views.philosophy, name="philosophy"),
    path("hare-krishna-movement", views.harekrsna_movement, name="harekrsna_movement"),
    path("temple-schedule", views.temple_schedule, name="temple_schedule"),
    path("resources", views.resources, name="resources"),

]
