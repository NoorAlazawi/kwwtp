from django.urls import path
from . import views

urlpatterns = [
    path("readings/new/", views.reading_create, name="reading_create"),
    path("readings/bulk/", views.reading_bulk_create, name="reading_bulk_create"),
    path("readings/form/", views.reading_form, name="reading_form"),
    path("readings/<int:pk>/edit/", views.reading_edit, name="reading_edit"),
    path("readings/delete/", views.reading_delete, name="reading_delete"),
    path("readings/", views.reading_list, name="reading_list"),
]
