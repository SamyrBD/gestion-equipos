"""Prueba directa de los 8 microservicios (corre DENTRO del contenedor, solo usa la librería estándar).

Uso con Docker local:   docker exec <ID_DEL_CONTENEDOR> python /app/probar_microservicios.py
Uso en Render:          pestaña Shell del servicio -> python /app/probar_microservicios.py

Para cada lenguaje (Node.js y Go) hace: insertar -> consultar -> actualizar -> eliminar,
y comprueba también los errores (fecha inventada, id que no existe).
Usa el equipo 999999, que no existe, y borra lo que crea.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1"
CONSULTA = {"Python": f"{BASE}:8001/api", "Go": f"{BASE}:8002"}
INSERTAR = {"Node.js": f"{BASE}:8003", "Go": f"{BASE}:8006"}
ACTUALIZAR = {"Node.js": f"{BASE}:8004", "Go": f"{BASE}:8007"}
ELIMINAR = {"Node.js": f"{BASE}:8005", "Go": f"{BASE}:8008"}
EQUIPO_PRUEBA = 999999

fallos = 0


def pedir(metodo, url, datos=None):
    """Hace una petición HTTP y devuelve (codigo, json). Si no hay conexión: (None, mensaje)."""
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    peticion = urllib.request.Request(
        url, data=cuerpo, method=metodo, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(peticion, timeout=10) as respuesta:
            return respuesta.status, json.loads(respuesta.read() or b"null")
    except urllib.error.HTTPError as error:        # 4xx y 5xx llegan aquí
        try:
            return error.code, json.loads(error.read())
        except ValueError:
            return error.code, None
    except OSError as error:                       # sin conexión
        return None, str(error)


def comprobar(descripcion, condicion, detalle=""):
    global fallos
    print(("  ✔ " if condicion else "  ✘ ") + descripcion + ("" if condicion else f"   -> {detalle}"))
    if not condicion:
        fallos += 1


print("== 1. /health de los 8 servicios ==")
todos = {**{f"consulta {k}": v for k, v in CONSULTA.items()},
         **{f"insertar {k}": v for k, v in INSERTAR.items()},
         **{f"actualizar {k}": v for k, v in ACTUALIZAR.items()},
         **{f"eliminar {k}": v for k, v in ELIMINAR.items()}}
for nombre, url in todos.items():
    codigo, cuerpo = pedir("GET", f"{url}/health")
    comprobar(f"{nombre}", codigo == 200, f"{codigo} {cuerpo}")

for lenguaje in ("Node.js", "Go"):
    print(f"\n== 2. Ciclo completo con {lenguaje} ==")
    codigo, creado = pedir("POST", f"{INSERTAR[lenguaje]}/mantenimientos", {
        "equipo_id": EQUIPO_PRUEBA, "fecha": "2026-09-18",
        "descripcion": f"Prueba {lenguaje}", "tecnico": "Script de pruebas"})
    comprobar("insertar -> 201 con id", codigo == 201 and isinstance(creado, dict) and "id" in creado, f"{codigo} {creado}")
    if codigo != 201:
        continue
    nuevo_id = creado["id"]
    comprobar("la fecha vuelve como AAAA-MM-DD", creado["fecha"] == "2026-09-18", creado.get("fecha"))

    for servicio, url in CONSULTA.items():
        codigo, lista = pedir("GET", f"{url}/mantenimientos/{EQUIPO_PRUEBA}")
        ids = [m["id"] for m in lista] if isinstance(lista, list) else []
        comprobar(f"consultar con {servicio} lo encuentra", codigo == 200 and nuevo_id in ids, f"{codigo} {lista}")

    codigo, cambiado = pedir("PUT", f"{ACTUALIZAR[lenguaje]}/mantenimientos/{nuevo_id}", {
        "fecha": "2026-09-19", "descripcion": "Texto cambiado", "tecnico": "Otro técnico"})
    comprobar("actualizar -> 200 con los datos nuevos",
              codigo == 200 and isinstance(cambiado, dict) and cambiado.get("descripcion") == "Texto cambiado",
              f"{codigo} {cambiado}")

    codigo, resp = pedir("DELETE", f"{ELIMINAR[lenguaje]}/mantenimientos/{nuevo_id}")
    comprobar("eliminar -> 200", codigo == 200, f"{codigo} {resp}")
    codigo, resp = pedir("DELETE", f"{ELIMINAR[lenguaje]}/mantenimientos/{nuevo_id}")
    comprobar("eliminar otra vez -> 404", codigo == 404, f"{codigo} {resp}")
    codigo, resp = pedir("PUT", f"{ACTUALIZAR[lenguaje]}/mantenimientos/{nuevo_id}", {
        "fecha": "2026-09-19", "descripcion": "x", "tecnico": "y"})
    comprobar("actualizar un id borrado -> 404", codigo == 404, f"{codigo} {resp}")
    codigo, resp = pedir("POST", f"{INSERTAR[lenguaje]}/mantenimientos", {
        "equipo_id": EQUIPO_PRUEBA, "fecha": "2026-02-31", "descripcion": "x", "tecnico": "y"})
    comprobar("insertar con fecha 2026-02-31 -> 400", codigo == 400, f"{codigo} {resp}")

print("\n" + ("TODO BIEN ✔" if fallos == 0 else f"HAY {fallos} PRUEBA(S) FALLIDA(S) ✘"))
sys.exit(1 if fallos else 0)