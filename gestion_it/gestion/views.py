from django.shortcuts import render
from departamentos.models import Departamento
from equipos.models import Equipo

def inicio(request):
    equipos = Equipo.objects.all()
    en_reparacion = equipos.filter(estado=Equipo.ESTADO_REPARACION)

    context = {
        "total_equipos": equipos.count(),
        "total_departamentos": Departamento.objects.count(),
        "total_activos": equipos.filter(estado=Equipo.ESTADO_ACTIVO).count(),
        "total_reparacion": en_reparacion.count(),
        "total_baja": equipos.filter(estado=Equipo.ESTADO_BAJA).count(),
        "equipos_en_reparacion": en_reparacion.select_related("departamento")[:5],
    }
    return render(request, "inicio.html", context)