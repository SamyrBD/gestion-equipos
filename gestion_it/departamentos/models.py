from django.db import models

class Departamento(models.Model):
    nombre = models.CharField("Nombre del Departamento", max_length=100)
    encargado = models.CharField("Encargado", max_length=100)

    def __str__(self):
        return self.nombre