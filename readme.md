# Gestión de equipos tecnológicos + microservicio de mantenimientos

## Problemática
Las empresas pequeñas con varios equipos tecnológicos (computadores, impresoras, equipos de red) no llevan un registro centralizado de cuándo se les hizo mantenimiento ni qué fallas han tenido. Un equipo falla sin aviso porque nadie sabía que ya tocaba revisarlo, o se repite un mantenimiento ya hecho.

## Solución y arquitectura
Un repositorio, dos proyectos Django independientes:

| Carpeta | Rol | Base de datos | Dónde corre |
|---|---|---|---|
| `gestion_ti/` | Catálogo de departamentos y equipos; consume el microservicio | SQLite | Local (por ahora) |
| `microservicio_mantenimientos/` | API JSON con el historial de mantenimientos | PostgreSQL en Supabase | Render: https://TU-SERVICIO.onrender.com |

Flujo: `equipos.detail()` → `requests.get(MICROSERVICIO_URL/mantenimientos/<id>/)` → microservicio → Supabase.

## Estado del despliegue
- Microservicio: desplegado en Render (plan gratis; la primera petición tras un rato de inactividad tarda cerca de un minuto).
- Proyecto principal: corre en local apuntando al microservicio real vía `MICROSERVICIO_URL`.

## Cómo correrlo en local
1. En cada carpeta: `py -m venv .venv`, activar y `py -m pip install -r requirements.txt`.
2. Crear un `.env` en cada carpeta: `gestion_ti` necesita `MICROSERVICIO_URL`; `microservicio_mantenimientos` necesita `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT`.
3. `gestion_ti`: `python manage.py migrate` y `python manage.py runserver 8000`.
4. (Opcional, para probar cambios del microservicio) `microservicio_mantenimientos`: `python manage.py runserver 8001` y `MICROSERVICIO_URL=http://127.0.0.1:8001`.