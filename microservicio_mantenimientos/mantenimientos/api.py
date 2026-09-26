from datetime import date
from ninja import NinjaAPI, Schema
from .models import Mantenimiento

api = NinjaAPI(title="API de mantenimientos", version="1.0")

class MantenimientoOut(Schema):
    fecha: date
    descripcion: str
    tecnico: str

@api.get("/mantenimientos/{equipo_id}", response=list[MantenimientoOut])
def por_equipo(request, equipo_id: int):
    return Mantenimiento.objects.filter(equipo_id=equipo_id).order_by("-fecha")

@api.get("/mantenimientos/{equipo_id}/total")
def total(request, equipo_id: int):
    cantidad = Mantenimiento.objects.filter(equipo_id=equipo_id).count()
    return {"equipo_id": equipo_id, "total": cantidad}

class MantenimientoIn(Schema):
    equipo_id: int
    fecha: date
    descripcion: str
    tecnico: str

@api.post("/mantenimientos", response={201: MantenimientoOut})
def crear(request, datos: MantenimientoIn):
    return 201, Mantenimiento.objects.create(**datos.dict())