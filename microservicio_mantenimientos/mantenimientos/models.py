from django.db import models

class Mantenimiento(models.Model):
    equipo_id = models.IntegerField()
    fecha = models.DateField()
    descripcion = models.TextField()
    tecnico = models.CharField(max_length=100)

    def __str__(self):
        return f"Equipo {self.equipo_id} — {self.fecha}"