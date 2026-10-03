# ===== Etapa 1: compilar los 4 microservicios en Go =====
FROM golang:1.22-bookworm AS compilar_go
WORKDIR /src
COPY ms_go/ ./
RUN go mod tidy
RUN CGO_ENABLED=0 go build -o /salida/consulta_go ./consulta \
 && CGO_ENABLED=0 go build -o /salida/insertar_go ./insertar \
 && CGO_ENABLED=0 go build -o /salida/actualizar_go ./actualizar \
 && CGO_ENABLED=0 go build -o /salida/eliminar_go ./eliminar

# ===== Etapa 2: imagen final (Python + Node.js + los ejecutables de Go) =====
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

# Node.js para los 3 microservicios de ms_node (Go no hace falta: ya viene compilado)
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Dependencias de Python (Django, Ninja, gunicorn, supervisor...)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Todo el código del repositorio
COPY . .

# 3) Instalar express y pg para los microservicios de Node.js
RUN cd ms_node && npm install --omit=dev

# 4) Traer los ejecutables de Go compilados en la etapa 1
COPY --from=compilar_go /salida/ /app/bin/

# 5) Archivos estáticos de gestion_ti (CSS) para WhiteNoise
RUN python manage.py collectstatic --noinput

RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]