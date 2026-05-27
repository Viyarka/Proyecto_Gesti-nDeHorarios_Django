from django.contrib import admin
from .models import (
    Asignatura,
    AuditLog,
    Aula,
    Curso,
    DisponibilidadProfesor,
    FranjaHoraria,
    Grupo,
    HistorialDisponibilidad,
    Horario,
    Notificacion,
    PerfilAlumno,
    Profesor,
    ProfesorSuplente,
    Sesion,
    Titulacion,
)


@admin.register(Titulacion)
class TitulacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "duracion_anios", "permite_manana_tarde")
    search_fields = ("nombre", "codigo")


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("titulacion", "numero", "nombre")
    list_filter = ("titulacion", "numero")
    search_fields = ("nombre", "titulacion__nombre")


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "curso", "tipo")
    list_filter = ("tipo", "curso__titulacion")
    search_fields = ("nombre", "curso__nombre", "curso__titulacion__nombre")


@admin.register(Profesor)
class ProfesorAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "email", "area_conocimiento")
    search_fields = ("codigo", "nombre", "email")


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "capacidad", "recursos")
    search_fields = ("nombre",)


class ProfesorSuplenteInline(admin.TabularInline):
    model = ProfesorSuplente
    extra = 0
    autocomplete_fields = ("profesor",)


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "curso", "profesor_titular", "sesiones_semanales", "horas_por_sesion", "es_transversal", "codigo_global_compartido")
    list_filter = ("curso__titulacion", "curso__numero", "es_transversal")
    search_fields = ("codigo", "nombre", "codigo_global_compartido")
    autocomplete_fields = ("profesor_titular", "aula_preferente")
    inlines = [ProfesorSuplenteInline]


@admin.register(ProfesorSuplente)
class ProfesorSuplenteAdmin(admin.ModelAdmin):
    list_display = ("asignatura", "profesor", "area_conocimiento", "prioridad", "activo")
    list_filter = ("activo", "area_conocimiento")
    search_fields = ("asignatura__nombre", "profesor__nombre", "profesor__codigo", "area_conocimiento")
    autocomplete_fields = ("asignatura", "profesor")


@admin.register(FranjaHoraria)
class FranjaHorariaAdmin(admin.ModelAdmin):
    list_display = ("dia", "hora_inicio", "hora_fin", "activa")
    list_filter = ("dia", "activa")
    search_fields = ("dia", "etiqueta")


@admin.register(DisponibilidadProfesor)
class DisponibilidadProfesorAdmin(admin.ModelAdmin):
    list_display = ("profesor", "franja", "estado", "motivo")
    list_filter = ("estado", "franja__dia")
    search_fields = ("profesor__nombre", "profesor__codigo")
    autocomplete_fields = ("profesor", "franja")


@admin.register(HistorialDisponibilidad)
class HistorialDisponibilidadAdmin(admin.ModelAdmin):
    list_display = ("creado", "profesor", "franja", "estado", "usuario")
    list_filter = ("estado", "franja__dia")
    search_fields = ("profesor__nombre", "profesor__codigo", "motivo")
    readonly_fields = ("creado", "actualizado")


class SesionInline(admin.TabularInline):
    model = Sesion
    extra = 0
    autocomplete_fields = ("asignatura", "profesor", "aula", "grupo", "franja")


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ("anio_academico", "semestre", "titulacion", "curso", "estado", "aprobado_por")
    list_filter = ("anio_academico", "semestre", "estado", "titulacion")
    search_fields = ("anio_academico", "titulacion__nombre", "curso__nombre")
    inlines = [SesionInline]


@admin.register(Sesion)
class SesionAdmin(admin.ModelAdmin):
    list_display = ("horario", "asignatura", "profesor", "aula", "grupo", "franja")
    list_filter = ("horario__semestre", "franja__dia", "grupo", "aula")
    search_fields = ("asignatura__nombre", "asignatura__codigo", "profesor__codigo", "grupo__nombre")
    autocomplete_fields = ("horario", "asignatura", "profesor", "aula", "grupo", "franja")


@admin.register(PerfilAlumno)
class PerfilAlumnoAdmin(admin.ModelAdmin):
    list_display = ("user", "grupo")
    search_fields = ("user__username", "user__first_name", "user__last_name", "grupo__nombre")
    filter_horizontal = ("asignaturas",)


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "nivel", "titulo", "leida", "creado")
    list_filter = ("nivel", "leida")
    search_fields = ("usuario__username", "titulo", "mensaje")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("creado", "usuario", "accion", "modelo", "objeto_id")
    list_filter = ("accion", "modelo")
    search_fields = ("descripcion", "usuario__username")
    readonly_fields = ("creado", "actualizado")
