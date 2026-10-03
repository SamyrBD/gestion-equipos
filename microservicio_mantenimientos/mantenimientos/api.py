from datetime import date

from django.db import connection
from ninja import NinjaAPI, Schema

from .models import Mantenimiento

api = NinjaAPI(title="API de consulta de mantenimientos", version="2.0")


class MantenimientoOut(Schema):
    id: int
    equipo_id: int
    fecha: date
    descripcion: str
    tecnico: str


@api.get("/health", response={200: dict, 503: dict})
def health(request):
    """Lo consulta el monitor de gestion_ti para saber si el servicio está vivo."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as error:
        return 503, {"status": "error", "detalle": str(error)}
    return 200, {"status": "ok", "servicio": "consulta-django-ninja", "lenguaje": "Python"}


@api.get("/mantenimientos/{equipo_id}", response=list[MantenimientoOut])
def por_equipo(request, equipo_id: int):
    return Mantenimiento.objects.filter(equipo_id=equipo_id).order_by("-fecha", "-id")


@api.get("/mantenimientos/{equipo_id}/total")
def total(request, equipo_id: int):
    cantidad = Mantenimiento.objects.filter(equipo_id=equipo_id).count()
    return {"equipo_id": equipo_id, "total": cantidad}