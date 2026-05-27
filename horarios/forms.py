from django import forms
from .models import DisponibilidadProfesor, FranjaHoraria, Horario, PerfilAlumno, ProfesorSuplente, Sesion


class HorarioFilterForm(forms.Form):
    anio_academico = forms.CharField(required=False, label="Año académico")
    semestre = forms.ChoiceField(
        required=False,
        choices=[("", "Todos"), ("1", "Primer semestre"), ("2", "Segundo semestre")],
        label="Semestre",
    )
    titulacion = forms.CharField(required=False, label="Titulación")
    curso = forms.IntegerField(required=False, min_value=1, label="Curso")
    grupo = forms.CharField(required=False, label="Grupo")
    profesor = forms.CharField(required=False, label="Profesor")
    asignatura = forms.CharField(required=False, label="Asignatura")


class HorarioForm(forms.ModelForm):
    class Meta:
        model = Horario
        fields = ["anio_academico", "semestre", "titulacion", "curso", "estado"]
        widgets = {
            "anio_academico": forms.TextInput(attrs={"placeholder": "2025-2026"}),
        }


class SesionForm(forms.ModelForm):
    class Meta:
        model = Sesion
        fields = ["horario", "asignatura", "profesor", "aula", "grupo", "franja", "observaciones"]


class DisponibilidadProfesorForm(forms.ModelForm):
    class Meta:
        model = DisponibilidadProfesor
        fields = ["profesor", "franja", "estado", "motivo"]


class GenerarHorarioForm(forms.Form):
    horario = forms.ModelChoiceField(queryset=Horario.objects.all(), label="Horario")
    sobrescribir = forms.BooleanField(required=False, label="Borrar sesiones actuales antes de generar")


class GenerarGlobalForm(forms.Form):
    anio_academico = forms.CharField(label="Año académico", initial="2025-2026")
    semestre = forms.ChoiceField(choices=[("1", "Primer semestre"), ("2", "Segundo semestre")], label="Semestre")
    sobrescribir = forms.BooleanField(required=False, label="Borrar sesiones actuales antes de generar")


class ConfiguracionFranjaForm(forms.ModelForm):
    class Meta:
        model = FranjaHoraria
        fields = ["dia", "hora_inicio", "hora_fin", "etiqueta", "activa"]
        widgets = {
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}),
            "hora_fin": forms.TimeInput(attrs={"type": "time"}),
        }


class PerfilAlumnoForm(forms.ModelForm):
    class Meta:
        model = PerfilAlumno
        fields = ["grupo", "asignaturas"]
        widgets = {
            "asignaturas": forms.CheckboxSelectMultiple,
        }


class ProfesorSuplenteForm(forms.ModelForm):
    class Meta:
        model = ProfesorSuplente
        fields = ["asignatura", "profesor", "area_conocimiento", "prioridad", "activo"]
