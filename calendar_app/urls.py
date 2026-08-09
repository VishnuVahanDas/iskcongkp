from django.urls import path

from . import views

app_name = "calendar_app"
urlpatterns = [
    path('calendar/', views.CalendarListView.as_view(), name='vaishnava_calendar'),
    path('calendar/ekadashi/', views.EkadashiListView.as_view(), name='ekadashi_list'),
    path('calendar/appearance-days/', views.AppearanceDayListView.as_view(), name='appearance_days'),
    path('calendar/disappearance-days/', views.DisappearanceDayListView.as_view(), name='disappearance_days'),
    path('calendar/festivals/', views.FestivalListView.as_view(), name='festivals'),
    path('events/', views.TempleEventListView.as_view(), name='temple_events'),
    path('api/calendar/<int:year>/', views.calendar_api_json, name='calendar_api'),
]
