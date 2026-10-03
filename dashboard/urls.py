from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("monitor/", views.monitor_screen, name="monitor_screen"),
    path("rec/add/", views.rec_add, name="rec_add"),
    path("rec/<int:pk>/toggle/", views.rec_toggle, name="rec_toggle"),
    path("rec/<int:pk>/edit/", views.rec_edit, name="rec_edit"),
    path("rec/<int:pk>/delete/", views.rec_delete, name="rec_delete"),
    path("alarm/<int:pk>/edit/", views.alarm_edit, name="alarm_edit"),
]
