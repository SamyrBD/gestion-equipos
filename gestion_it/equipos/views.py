import os
import requests
from django.shortcuts import render, get_object_or_404
from .models import Equipo

MICROSERVICIO_URL = os.environ.get("MICROSERVICIO_URL", "http://127.0.0.1:8001")

def index(request):
    lista_equipos = Equipo.objects.all()
    context = {"lista_equipos": lista_equipos}
    return render(request, "equipos/index.html", context)

def detail(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)

    url_endpoint = f"{MICROSERVICIO_URL}/mantenimientos/{equipo_id}/"
    try:
        respuesta = requests.get(url_endpoint, timeout=5)
        mantenimientos = respuesta.json() if respuesta.status_code == 200 else []
    except requests.exceptions.RequestException:
        mantenimientos = []

    context = {"equipo": equipo, "mantenimientos": mantenimientos}
    return render(request, "equipos/detail.html", context)

def por_estado(request, estado_code):
    equipos = Equipo.objects.filter(estado=estado_code.upper())
    context = {"estado_code": estado_code.upper(), "equipos": equipos, "total": equipos.count()}
    return render(request, "equipos/por_estado.html", context)