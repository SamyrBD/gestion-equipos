from django.http import JsonResponse
from .models import Mantenimiento

def por_equipo(request, equipo_id):
    registros = Mantenimiento.objects.filter(equipo_id=equipo_id).values(
        "fecha", "descripcion", "tecnico"
    )
    return JsonResponse(list(registros), safe=False)