
from django import forms
from .models import PerfilUsuario

class FotoPerfilForm(forms.ModelForm):
    class Meta:
        model = PerfilUsuario
        fields = ["foto"]
