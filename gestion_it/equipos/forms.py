from django import forms
from .models import Equipo

# format="%Y-%m-%d" hace que el <input type="date"> muestre la fecha al editar
# (sin esto, con idioma español el campo puede aparecer vacío)
FECHA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ["nombre", "departamento", "tipo", "estado", "fecha_compra"]
        widgets = {"fecha_compra": FECHA}


class MantenimientoForm(forms.Form):
    """Formulario SIN modelo: el mantenimiento vive en otro servicio, no en la base de gestion_ti."""
    fecha = forms.DateField(label="Fecha", widget=FECHA)
    descripcion = forms.CharField(label="Descripción", max_length=200)
    tecnico = forms.CharField(label="Técnico", max_length=100)