import os

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from . import servicios
from .forms import EquipoForm, MantenimientoForm
from .models import Equipo

MODELO_IA = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")


def index(request):
    lista_equipos = Equipo.objects.all()
    return render(request, "equipos/index.html", {"lista_equipos": lista_equipos})


def detail(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)

    # La resiliencia vive en servicios.py: aquí solo pedimos los datos
    mantenimientos, servicio = servicios.consultar_mantenimientos(equipo_id)

    context = {
        "equipo": equipo,
        "mantenimientos": mantenimientos or [],
        "servicio": servicio,                        # microservicio que respondió (None si ninguno)
        "microservicio_ok": mantenimientos is not None,
        "usando_respaldo": servicio is not None and servicio["clave"] != "consulta_principal",
    }
    return render(request, "equipos/detail.html", context)


def por_estado(request, estado_code):
    equipos = Equipo.objects.filter(estado=estado_code.upper())
    context = {"estado_code": estado_code.upper(), "equipos": equipos, "total": equipos.count()}
    return render(request, "equipos/por_estado.html", context)


def estado_microservicios(request):
    """Panel de monitoreo: muestra qué microservicios están vivos ahora mismo."""
    estados = servicios.estado_servicios(forzar=True)
    consulta_activa = next((s for s in estados if s["rol"] == "consulta" and s["vivo"]), None)
    return render(request, "equipos/servicios.html", {
        "servicios": estados,
        "consulta_activa": consulta_activa,
        "puede_controlar": servicios.puede_controlar(),
    })


def controlar_servicio(request, clave, accion):
    """Apaga o enciende un microservicio (solo POST). Sirve para demostrar la resiliencia."""
    if request.method == "POST":
        ok, mensaje = servicios.controlar(clave, accion)
        if ok:
            messages.success(request, f"Servicio {'apagado' if accion == 'stop' else 'encendido'}.")
        else:
            messages.error(request, f"No se pudo completar la acción: {mensaje}")
    return redirect("equipos:servicios")


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
            # La librería de IA se importa aquí (y no arriba) para no gastar memoria
            # mientras nadie use el chat, y para que una key faltante solo afecte al chat.
            from google import genai
            from google.genai import errors, types

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

                cliente = genai.Client(
                    api_key=os.environ.get("GEMINI_API_KEY"),
                    http_options=types.HttpOptions(timeout=30000),  # 30 s, en milisegundos
                )
                chat_session = cliente.chats.create(
                    model=MODELO_IA,
                    history=mensajes_api,
                    config=types.GenerateContentConfig(system_instruction=instrucciones),
                )
                respuesta = chat_session.send_message(pregunta)

                historial.append({"role": "user", "content": pregunta})
                historial.append({"role": "assistant", "content": respuesta.text})

            except errors.APIError as e:
                if e.code == 429:
                    error = "Has hecho varias preguntas seguidas. Espera unos 30 segundos e inténtalo de nuevo."
                else:
                    error = "La IA no respondió. Revisa los registros del servidor para más detalles."
                print(f"Error de Gemini: {e}")
            except Exception as e:
                error = "La IA no respondió. Revisa que GEMINI_API_KEY esté configurada."
                print(f"Error de Gemini: {e}")

    request.session["chat"] = historial[-10:]
    return render(request, "equipos/chat.html", {"historial": historial, "error": error})


# ---------------------------------------------------------------------------
# CRUD de equipos (base de datos de gestion_ti)
# ---------------------------------------------------------------------------
def equipo_crear(request):
    if request.method == "POST":
        form = EquipoForm(request.POST)
        if form.is_valid():
            equipo = form.save()
            messages.success(request, "Equipo creado.")
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
            messages.success(request, "Cambios guardados.")
            return redirect("equipos:detail", equipo_id=equipo.id)
    else:
        form = EquipoForm(instance=equipo)
    return render(request, "equipos/equipo_form.html", {"form": form, "accion": "Editar", "equipo": equipo})


def equipo_eliminar(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == "POST":
        equipo.delete()
        messages.success(request, "Equipo eliminado.")
        return redirect("equipos:index")
    return render(request, "equipos/equipo_confirm_delete.html", {"equipo": equipo})


# ---------------------------------------------------------------------------
# CRUD de mantenimientos. Cada operación la hace un microservicio: primero el de Node.js
# y, si está apagado, el de Go (esa decisión la toma servicios.llamar()).
# ---------------------------------------------------------------------------
def mantenimiento_crear(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == "POST":
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            ok, resultado, quien = servicios.llamar("insertar", "POST", "/mantenimientos", {
                "equipo_id": equipo.id,
                "fecha": datos["fecha"].isoformat(),
                "descripcion": datos["descripcion"],
                "tecnico": datos["tecnico"],
            })
            if ok:
                messages.success(request, f"Mantenimiento registrado (servicio: {servicios.etiqueta(quien)}).")
                return redirect("equipos:detail", equipo_id=equipo.id)
            messages.error(request, resultado)
    else:
        form = MantenimientoForm()
    return render(request, "equipos/mantenimiento_form.html", {"form": form, "equipo": equipo, "accion": "Registrar"})


def mantenimiento_editar(request, equipo_id, mantenimiento_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == "POST":
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            ok, resultado, quien = servicios.llamar("actualizar", "PUT", f"/mantenimientos/{mantenimiento_id}", {
                "fecha": datos["fecha"].isoformat(),
                "descripcion": datos["descripcion"],
                "tecnico": datos["tecnico"],
            })
            if ok:
                messages.success(request, f"Mantenimiento actualizado (servicio: {servicios.etiqueta(quien)}).")
                return redirect("equipos:detail", equipo_id=equipo.id)
            messages.error(request, resultado)
    else:
        # Para rellenar el formulario buscamos el mantenimiento en la lista de la consulta
        lista, _ = servicios.consultar_mantenimientos(equipo_id)
        actual = next((m for m in (lista or []) if m["id"] == mantenimiento_id), None)
        if actual is None:
            messages.error(request, "No se encontró ese mantenimiento o el servicio de consulta no respondió.")
            return redirect("equipos:detail", equipo_id=equipo.id)
        form = MantenimientoForm(initial=actual)
    return render(request, "equipos/mantenimiento_form.html", {"form": form, "equipo": equipo, "accion": "Editar"})


def mantenimiento_eliminar(request, equipo_id, mantenimiento_id):
    if request.method == "POST":
        ok, resultado, quien = servicios.llamar("eliminar", "DELETE", f"/mantenimientos/{mantenimiento_id}")
        if ok:
            messages.success(request, f"Mantenimiento eliminado (servicio: {servicios.etiqueta(quien)}).")
        else:
            messages.error(request, resultado)
    return redirect("equipos:detail", equipo_id=equipo_id)