from django.urls import path
from . import views

app_name = "equipos"
urlpatterns = [
    path("", views.index, name="index"),
    path("<int:equipo_id>/", views.detail, name="detail"),
    path("estado/<str:estado_code>/", views.por_estado, name="por_estado"),
    path("chat/", views.chat, name="chat"),
    path("equipos/nuevo/", views.equipo_crear, name="equipo_crear"),
    path("equipos/<int:equipo_id>/editar/", views.equipo_editar, name="equipo_editar"),
    path("equipos/<int:equipo_id>/eliminar/", views.equipo_eliminar, name="equipo_eliminar"),
]