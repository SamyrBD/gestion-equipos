"""Comunicación de gestion_ti con los microservicios.

- consultar_mantenimientos(): lee con RESILIENCIA (principal en Python y, si cae, respaldo en Go).
- llamar(): insertar / actualizar / eliminar. Cada operación tiene un servicio en Node.js y
  otro en Go; si el primero está caído (no hay conexión), se usa el segundo.
- estado_servicios(): MONITOR que pregunta a cada microservicio si está vivo.
- controlar(): apaga o enciende un microservicio (solo para la demo).

Todos los microservicios corren en el MISMO contenedor, cada uno en su puerto interno.
"""
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import requests


def _url(variable, por_defecto):
    """Lee la URL desde una variable de entorno y le quita el '/' final."""
    return os.environ.get(variable, por_defecto).rstrip("/")


# ---------------------------------------------------------------------------
# 1. Catálogo de microservicios
#    operacion: qué hace ("consulta", "insertar", "actualizar", "eliminar").
#    respaldo:  False = se intenta primero; True = solo se usa si el anterior cae.
#    proceso:   nombre del programa en supervisord.conf (lo usan los botones Apagar/Encender).
#    El ORDEN de la lista es el orden de prioridad dentro de cada operación.
# ---------------------------------------------------------------------------
SERVICIOS = [
    {
        "clave": "consulta_principal", "operacion": "consulta", "rol": "consulta", "respaldo": False,
        "proceso": "consulta_python", "nombre": "Consulta principal", "lenguaje": "Python (Django Ninja)",
        "url": _url("CONSULTA_PRINCIPAL_URL", "http://127.0.0.1:8001/api"),
    },
    {
        "clave": "consulta_respaldo", "operacion": "consulta", "rol": "consulta", "respaldo": True,
        "proceso": "consulta_go", "nombre": "Consulta de respaldo", "lenguaje": "Go",
        "url": _url("CONSULTA_RESPALDO_URL", "http://127.0.0.1:8002"),
    },
    {
        "clave": "insertar_principal", "operacion": "insertar", "rol": "escritura", "respaldo": False,
        "proceso": "insertar_node", "nombre": "Inserción", "lenguaje": "Node.js",
        "url": _url("INSERTAR_URL", "http://127.0.0.1:8003"),
    },
    {
        "clave": "insertar_respaldo", "operacion": "insertar", "rol": "escritura", "respaldo": True,
        "proceso": "insertar_go", "nombre": "Inserción (respaldo)", "lenguaje": "Go",
        "url": _url("INSERTAR_RESPALDO_URL", "http://127.0.0.1:8006"),
    },
    {
        "clave": "actualizar_principal", "operacion": "actualizar", "rol": "escritura", "respaldo": False,
        "proceso": "actualizar_node", "nombre": "Actualización", "lenguaje": "Node.js",
        "url": _url("ACTUALIZAR_URL", "http://127.0.0.1:8004"),
    },
    {
        "clave": "actualizar_respaldo", "operacion": "actualizar", "rol": "escritura", "respaldo": True,
        "proceso": "actualizar_go", "nombre": "Actualización (respaldo)", "lenguaje": "Go",
        "url": _url("ACTUALIZAR_RESPALDO_URL", "http://127.0.0.1:8007"),
    },
    {
        "clave": "eliminar_principal", "operacion": "eliminar", "rol": "escritura", "respaldo": False,
        "proceso": "eliminar_node", "nombre": "Eliminación", "lenguaje": "Node.js",
        "url": _url("ELIMINAR_URL", "http://127.0.0.1:8005"),
    },
    {
        "clave": "eliminar_respaldo", "operacion": "eliminar", "rol": "escritura", "respaldo": True,
        "proceso": "eliminar_go", "nombre": "Eliminación (respaldo)", "lenguaje": "Go",
        "url": _url("ELIMINAR_RESPALDO_URL", "http://127.0.0.1:8008"),
    },
]
POR_CLAVE = {s["clave"]: s for s in SERVICIOS}

TIMEOUT_SALUD = 3        # segundos para responder /health (son servicios locales)
TIMEOUT_CONSULTA = 5     # segundos para responder una consulta
TIMEOUT_ESCRITURA = 10   # segundos para insertar, actualizar o eliminar
SEGUNDOS_CACHE = 10      # cada cuánto se vuelve a revisar el estado

_cache = {"hora": 0.0, "estados": []}


def etiqueta(servicio):
    """Texto corto para mostrar quién atendió, por ejemplo 'Node.js' o 'Go (respaldo)'."""
    if servicio is None:
        return ""
    return servicio["lenguaje"] + (" (respaldo)" if servicio["respaldo"] else "")


# ---------------------------------------------------------------------------
# 2. Monitor de estado
# ---------------------------------------------------------------------------
def _revisar(servicio):
    """Pregunta a UN microservicio si está vivo (GET /health)."""
    inicio = time.time()
    try:
        respuesta = requests.get(f"{servicio['url']}/health", timeout=TIMEOUT_SALUD)
        vivo = respuesta.status_code == 200
    except requests.exceptions.RequestException:
        vivo = False
    return {**servicio, "vivo": vivo, "ms": round((time.time() - inicio) * 1000)}


def estado_servicios(forzar=False):
    """Estado de todos los microservicios. Se guarda 10 s para no preguntar en cada petición."""
    if forzar or time.time() - _cache["hora"] > SEGUNDOS_CACHE:
        with ThreadPoolExecutor() as pool:          # los revisa en paralelo
            _cache["estados"] = list(pool.map(_revisar, SERVICIOS))
        _cache["hora"] = time.time()
    return _cache["estados"]


# ---------------------------------------------------------------------------
# 3. Consulta con resiliencia (principal en Python -> respaldo en Go)
# ---------------------------------------------------------------------------
def consultar_mantenimientos(equipo_id):
    """Devuelve (lista, servicio_que_respondió). Si ninguno responde: (None, None)."""
    estados = estado_servicios()
    if not any(s["vivo"] for s in estados if s["rol"] == "consulta"):
        estados = estado_servicios(forzar=True)     # según la caché no hay nadie: revisamos de nuevo
    for servicio in estados:
        if servicio["rol"] != "consulta" or not servicio["vivo"]:
            continue                                # saltamos los que están caídos
        try:
            respuesta = requests.get(
                f"{servicio['url']}/mantenimientos/{equipo_id}", timeout=TIMEOUT_CONSULTA
            )
            if respuesta.status_code == 200:
                return respuesta.json(), servicio
        except (requests.exceptions.RequestException, ValueError):
            pass
        servicio["vivo"] = False                    # falló en vivo: lo marcamos caído y probamos el siguiente
    return None, None


# ---------------------------------------------------------------------------
# 4. Escrituras con failover: Node.js primero, Go si Node.js está caído
# ---------------------------------------------------------------------------
def llamar(operacion, metodo, ruta, datos=None):
    """Ejecuta 'insertar', 'actualizar' o 'eliminar'.

    Devuelve (ok, resultado_o_mensaje_de_error, servicio_que_atendió).

    Regla de seguridad: solo pasamos al respaldo si NO se pudo conectar con el servicio
    (está apagado o caído). Si la petición llegó y se agotó el tiempo, NO reintentamos:
    el primero pudo haber guardado el dato y lo duplicaríamos.
    """
    candidatos = [s for s in SERVICIOS if s["operacion"] == operacion]
    for servicio in candidatos:
        try:
            respuesta = requests.request(
                metodo, f"{servicio['url']}{ruta}", json=datos, timeout=TIMEOUT_ESCRITURA
            )
        except requests.exceptions.ReadTimeout:
            return False, (
                f"El servicio de {operacion} ({servicio['lenguaje']}) tardó demasiado en responder. "
                "Revisa el historial antes de volver a intentarlo."
            ), servicio
        except requests.exceptions.RequestException:
            continue                                # no hubo conexión: probamos con el respaldo
        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = {}
        if respuesta.ok:
            return True, cuerpo, servicio
        # El servicio SÍ respondió con un error (datos inválidos, no existe...): no se cambia de servicio
        mensaje = cuerpo.get("error", f"El microservicio respondió con el error {respuesta.status_code}.")
        return False, mensaje, servicio
    return False, (
        f"Ningún microservicio de {operacion} respondió (Node.js ni Go). "
        "Revisa el panel de servicios e inténtalo de nuevo."
    ), None


# ---------------------------------------------------------------------------
# 5. Apagar / encender un microservicio (para demostrar la resiliencia)
#    Solo funciona dentro del contenedor (donde existe supervisorctl) y si
#    la variable PANEL_CONTROL vale 1.
# ---------------------------------------------------------------------------
CONFIG_SUPERVISOR = os.environ.get("SUPERVISOR_CONF", "/app/supervisord.conf")


def puede_controlar():
    return os.environ.get("PANEL_CONTROL") == "1" and shutil.which("supervisorctl") is not None


def controlar(clave, accion):
    """accion: 'stop' o 'start'. Devuelve (ok, mensaje)."""
    if accion not in ("stop", "start") or clave not in POR_CLAVE or not puede_controlar():
        return False, "Acción no permitida."
    proceso = POR_CLAVE[clave]["proceso"]
    try:
        resultado = subprocess.run(
            ["supervisorctl", "-c", CONFIG_SUPERVISOR, accion, proceso],
            capture_output=True, text=True, timeout=20,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False, "supervisorctl no respondió."
    _cache["hora"] = 0.0                            # fuerza que el monitor vuelva a revisar
    return resultado.returncode == 0, resultado.stdout.strip() or resultado.stderr.strip()