from django.urls import path
from .api import api  # Importa el objeto 'api' que configuraste con NinjaAPI

app_name = "mantenimientos"
urlpatterns = [
    # Esto conecta TODAS las rutas de Django Ninja de un solo golpe, incluyendo Swagger
    path("api/", api.urls),
]