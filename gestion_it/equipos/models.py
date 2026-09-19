from django.db import models
from django.utils import timezone

class Equipo(models.Model):
    TIPO_COMPUTADOR = "PC"
    TIPO_IMPRESORA = "IMP"
    TIPO_RED = "RED"
    TIPO_OTRO = "OTR"
    TIPO_CHOICES = [
        (TIPO_COMPUTADOR, "Computador"),
        (TIPO_IMPRESORA, "Impresora"),
        (TIPO_RED, "Equipo de red"),
        (TIPO_OTRO, "Otro"),
    ]

    ESTADO_ACTIVO = "ACT"
    ESTADO_REPARACION = "REP"
    ESTADO_BAJA = "BAJ"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_REPARACION, "En reparación"),
        (ESTADO_BAJA, "De baja"),
    ]

    nombre = models.CharField("Nombre del Equipo", max_length=100)
    tipo = models.CharField("Tipo", max_length=3, choices=TIPO_CHOICES, default=TIPO_COMPUTADOR)
    departamento = models.ForeignKey("departamentos.Departamento", on_delete=models.CASCADE)
    fecha_compra = models.DateField("Fecha de Compra", default=timezone.now)
    estado = models.CharField("Estado", max_length=3, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)

    def __str__(self):
        return self.nombre