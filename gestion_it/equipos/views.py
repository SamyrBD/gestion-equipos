import os
import requests
from django.shortcuts import get_object_or_404, redirect, render
from .models import Equipo
from .forms import EquipoForm
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=30000),
)

MICROSERVICIO_URL = os.environ.get("MICROSERVICIO_URL", "https://microservicio-mantenimientos.onrender.com")


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


def datos_para_la_ia():
    equipos = Equipo.objects.select_related("departamento").order_by("id")
    lineas = [
        f"- Equipo {e.id}: {e.nombre} ({e.get_tipo_display()}, "
        f"departamento {e.departamento.nombre}), estado: {e.get_estado_display()}"
        for e in equipos
    ]
    return "\n".join(lineas)


def chat(request):
    if request.method == "POST" and "nuevo" in request.POST:
        request.session["chat"] = []
        return redirect("equipos:chat")

    historial = request.session.get("chat", [])
    error = None

    if request.method == "POST":
        pregunta = request.POST.get("pregunta", "").strip()
        if pregunta:
            instrucciones = (
                "Eres un asistente de inteligencia artificial útil y conversacional. "
                "Tienes acceso al siguiente inventario de equipos de TI como contexto adicional:\n\n"
                f"{datos_para_la_ia()}\n\n"
                "Instrucciones:\n"
                "1. Si te preguntan por el inventario o los equipos, usa los datos de arriba.\n"
                "2. Si te preguntan sobre cualquier otro tema, responde de manera normal usando tu conocimiento general."
            )

            try:
                mensajes_api = []
                for msg in historial:
                    rol = "model" if msg["role"] == "assistant" else "user"
                    mensajes_api.append({"role": rol, "parts": [{"text": msg["content"]}]})

                chat_session = client.chats.create(
                    model="gemini-3.5-flash-lite",
                    history=mensajes_api,
                    config=types.GenerateContentConfig(system_instruction=instrucciones),
                )
                respuesta = chat_session.send_message(pregunta)

                historial.append({"role": "user", "content": pregunta})
                historial.append({"role": "assistant", "content": respuesta.text})

            except Exception as e:
                error = "La IA no respondió. Revisa la terminal para más detalles."
                print(f"Error de Gemini: {e}")

    request.session["chat"] = historial[-10:]
    return render(request, "equipos/chat.html", {"historial": historial, "error": error})

def equipo_crear(request):
    if request.method == "POST":
        form = EquipoForm(request.POST)
        if form.is_valid():
            equipo = form.save()
            return redirect("equipos:detail", equipo_id=equipo.id)
    else:
        form = EquipoForm()
    return render(request, "equipos/equipo_form.html", {"form": form, "accion": "Crear"})


def equipo_editar(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == "POST":
        form = EquipoForm(request.POST, instance=equipo)
        if form.is_valid():
            form.save()
            return redirect("equipos:detail", equipo_id=equipo.id)
    else:
        form = EquipoForm(instance=equipo)
    return render(request, "equipos/equipo_form.html", {"form": form, "accion": "Editar", "equipo": equipo})


def equipo_eliminar(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == "POST":
        equipo.delete()
        return redirect("equipos:index")
    return render(request, "equipos/equipo_confirm_delete.html", {"equipo": equipo})