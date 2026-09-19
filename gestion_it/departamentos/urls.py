from django.urls import path
from . import views

app_name = "departamentos"
urlpatterns = [
    path("", views.index, name="index"),
    path("<int:departamento_id>/", views.detail, name="detail"),
]