from django import forms
from .models import Equipo


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ["nombre", "departamento", "tipo", "estado", "fecha_compra"]
        widgets = {
            "fecha_compra": forms.DateInput(attrs={"type": "date"}),
        }