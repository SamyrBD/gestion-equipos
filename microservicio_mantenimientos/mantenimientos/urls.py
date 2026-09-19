from django.urls import path
from . import views

app_name = "mantenimientos"
urlpatterns = [
    path("mantenimientos/<int:equipo_id>/", views.por_equipo, name="por_equipo"),
]