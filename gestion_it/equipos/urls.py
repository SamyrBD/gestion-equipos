from django.urls import path
from . import views

app_name = "equipos"
urlpatterns = [
    path("", views.index, name="index"),
    path("<int:equipo_id>/", views.detail, name="detail"),
    path("estado/<str:estado_code>/", views.por_estado, name="por_estado"),
    path("chat/", views.chat, name="chat"),
]