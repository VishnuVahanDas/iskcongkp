from django.urls import path

from . import views

app_name = "donation"
urlpatterns = [
    path("", views.shastra_daan, name="shastra_daan"),
    path("shastra-daan", views.shastra_daan, name="shastra_daan"),
    path("temple-seva", views.temple_seva, name="temple_seva"),
    path("annadana-seva", views.annadana_seva, name="annadana_seva"),
    path("nitya-seva", views.nitya_seva, name="nitya_seva"),
    path("janmashtami-seva", views.janmashtami_seva, name="janmashtami_seva"),
    path("tula-daan-utsav", views.tula_daan, name="tula_daan"),
    path("donate-a-brick", views.donate_brick, name="donate_brick"),
    

]
