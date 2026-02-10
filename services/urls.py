from django.urls import path

from . import views

app_name = "activities"
urlpatterns = [
    path("sunday-feast", views.sunday_feast, name="sunday_feast"),
    path("life-membership", views.life_member, name="life_member"),
    path("harinam-sankirtana", views.harinam, name="harinam"),
    path("youth-forum", views.iyf, name="iyf"),
    path("krishna-fun-school", views.krsna_school, name="krsna_school"),
    path("courses", views.courses, name="courses"),
    path("shiksha", views.shiksha, name="shiksha"),
]
