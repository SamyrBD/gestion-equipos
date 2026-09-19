from django.shortcuts import render, get_object_or_404
from .models import Departamento

def index(request):
    lista_departamentos = Departamento.objects.all()
    context = {"lista_departamentos": lista_departamentos}
    return render(request, "departamentos/index.html", context)

def detail(request, departamento_id):
    departamento = get_object_or_404(Departamento, pk=departamento_id)
    equipos_del_departamento = departamento.equipo_set.all()
    context = {
        "departamento": departamento,
        "equipos_del_departamento": equipos_del_departamento,
        "total_equipos": equipos_del_departamento.count(),
    }
    return render(request, "departamentos/detail.html", context)