from django.urls import path
from . import views

app_name = "equipos"
urlpatterns = [
    path("", views.index, name="index"),
    path("<int:equipo_id>/", views.detail, name="detail"),
    path("estado/<str:estado_code>/", views.por_estado, name="por_estado"),
    path("chat/", views.chat, name="chat"),
    path("servicios/", views.estado_microservicios, name="servicios"),
    path("servicios/<str:clave>/<str:accion>/", views.controlar_servicio, name="controlar_servicio"),
    # CRUD de equipos (base local)
    path("nuevo/", views.equipo_crear, name="equipo_crear"),
    path("<int:equipo_id>/editar/", views.equipo_editar, name="equipo_editar"),
    path("<int:equipo_id>/eliminar/", views.equipo_eliminar, name="equipo_eliminar"),
    # CRUD de mantenimientos (se hace a través de los microservicios)
    path("<int:equipo_id>/mantenimientos/nuevo/", views.mantenimiento_crear, name="mantenimiento_crear"),
    path("<int:equipo_id>/mantenimientos/<int:mantenimiento_id>/editar/", views.mantenimiento_editar, name="mantenimiento_editar"),
    path("<int:equipo_id>/mantenimientos/<int:mantenimiento_id>/eliminar/", views.mantenimiento_eliminar, name="mantenimiento_eliminar"),
]