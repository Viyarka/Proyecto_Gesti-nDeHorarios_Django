from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class TimeStampedModel(models.Model):
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Titulacion(TimeStampedModel):
    nombre = models.CharField(max_length=120, unique=True)
    codigo = models.SlugField(max_length=30, unique=True)
    duracion_anios = models.PositiveSmallIntegerField(default=4)
    permite_manana_tarde = models.BooleanField(default=False)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "titulación"
        verbose_name_plural = "titulaciones"

    def __str__(self):
        return self.nombre


class Curso(TimeStampedModel):
    titulacion = models.ForeignKey(Titulacion, on_delete=models.CASCADE, related_name="cursos")
    numero = models.PositiveSmallIntegerField()
    nombre = models.CharField(max_length=80, blank=True)

    class Meta:
        unique_together = ("titulacion", "numero")
        ordering = ["titulacion__nombre", "numero"]

    def __str__(self):
        return self.nombre or f"{self.numero}º - {self.titulacion.codigo}"


class Grupo(TimeStampedModel):
    TIPO_CHOICES = [
        ("TEORIA", "Teoría"),
        ("PRACTICAS", "Prácticas"),
        ("LAB", "Laboratorio"),
    ]

    nombre = models.CharField(max_length=40, unique=True)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="grupos")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="TEORIA")

    class Meta:
        ordering = ["curso__numero", "nombre"]

    def __str__(self):
        return self.nombre


class Profesor(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    nombre = models.CharField(max_length=120)
    codigo = models.CharField(max_length=30, unique=True)
    area_conocimiento = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "profesores"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Aula(TimeStampedModel):
    nombre = models.CharField(max_length=80, unique=True)
    capacidad = models.PositiveIntegerField(default=30)
    recursos = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Asignatura(TimeStampedModel):
    SEMESTRE_CHOICES = [("1", "Primer semestre"), ("2", "Segundo semestre")]

    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=160)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="asignaturas")
    semestre = models.CharField(max_length=1, choices=SEMESTRE_CHOICES, default="1")
    profesor_titular = models.ForeignKey(Profesor, on_delete=models.SET_NULL, null=True, blank=True, related_name="asignaturas")
    aula_preferente = models.ForeignKey(Aula, on_delete=models.SET_NULL, null=True, blank=True)
    sesiones_semanales = models.PositiveSmallIntegerField(default=2)
    horas_por_sesion = models.PositiveSmallIntegerField(default=2)
    es_transversal = models.BooleanField(default=False)
    codigo_global_compartido = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["curso__titulacion__nombre", "curso__numero", "nombre"]

    def __str__(self):
        return self.nombre

    @property
    def horas_totales_requeridas(self):
        return self.sesiones_semanales * self.horas_por_sesion


class ProfesorSuplente(TimeStampedModel):
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name="suplentes")
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE, related_name="suplencias")
    area_conocimiento = models.CharField(max_length=120)
    prioridad = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["asignatura__nombre", "prioridad", "profesor__nombre"]
        unique_together = ("asignatura", "profesor")
        verbose_name = "profesor suplente"
        verbose_name_plural = "profesores suplentes"

    def __str__(self):
        return f"{self.profesor} suplente de {self.asignatura}"


class FranjaHoraria(TimeStampedModel):
    DIA_CHOICES = [
        ("LUNES", "Lunes"),
        ("MARTES", "Martes"),
        ("MIÉRCOLES", "Miércoles"),
        ("JUEVES", "Jueves"),
        ("VIERNES", "Viernes"),
    ]

    dia = models.CharField(max_length=10, choices=DIA_CHOICES)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    etiqueta = models.CharField(max_length=50, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ("dia", "hora_inicio", "hora_fin")
        ordering = ["dia", "hora_inicio"]
        verbose_name = "franja horaria"
        verbose_name_plural = "franjas horarias"

    def __str__(self):
        return f"{self.get_dia_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"

    @property
    def duracion_horas(self):
        inicio = self.hora_inicio.hour * 60 + self.hora_inicio.minute
        fin = self.hora_fin.hour * 60 + self.hora_fin.minute
        return max((fin - inicio) / 60, 0)

    @property
    def es_tarde(self):
        return self.hora_inicio.hour >= 15

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de fin debe ser posterior a la hora de inicio."})


class DisponibilidadProfesor(TimeStampedModel):
    ESTADO_CHOICES = [
        ("PREFERENTE", "Disponibilidad preferente"),
        ("DISPONIBLE", "Disponible"),
        ("BLOQUEADO", "Indisponible"),
    ]

    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE, related_name="disponibilidades")
    franja = models.ForeignKey(FranjaHoraria, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="DISPONIBLE")
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("profesor", "franja")
        verbose_name = "disponibilidad de profesor"
        verbose_name_plural = "disponibilidades de profesores"

    def __str__(self):
        return f"{self.profesor.codigo} - {self.franja} - {self.estado}"


class HistorialDisponibilidad(TimeStampedModel):
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE, related_name="historial_disponibilidad")
    franja = models.ForeignKey(FranjaHoraria, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=DisponibilidadProfesor.ESTADO_CHOICES)
    motivo = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "historial de disponibilidad"
        verbose_name_plural = "historial de disponibilidades"

    def __str__(self):
        return f"{self.profesor.codigo} - {self.franja} - {self.estado}"


class Horario(TimeStampedModel):
    ESTADO_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("REVISION", "En revisión"),
        ("APROBADO", "Aprobado"),
        ("RECHAZADO", "Rechazado"),
    ]

    anio_academico = models.CharField(max_length=20, default="2025-2026")
    semestre = models.CharField(max_length=1, choices=[("1", "Primer semestre"), ("2", "Segundo semestre")])
    titulacion = models.ForeignKey(Titulacion, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="BORRADOR")
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="horarios_aprobados")
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("anio_academico", "semestre", "titulacion", "curso")
        ordering = ["anio_academico", "semestre", "titulacion__nombre", "curso__numero"]

    def __str__(self):
        return f"{self.titulacion.codigo} {self.curso.numero}º - S{self.semestre} ({self.anio_academico})"

    def get_absolute_url(self):
        return reverse("horario_detalle", args=[str(self.id)])


class Sesion(TimeStampedModel):
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE, related_name="sesiones")
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name="sesiones")
    profesor = models.ForeignKey(Profesor, on_delete=models.PROTECT, related_name="sesiones")
    aula = models.ForeignKey(Aula, on_delete=models.PROTECT, related_name="sesiones")
    grupo = models.ForeignKey(Grupo, on_delete=models.PROTECT, related_name="sesiones")
    franja = models.ForeignKey(FranjaHoraria, on_delete=models.PROTECT, related_name="sesiones")
    observaciones = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ["franja__dia", "franja__hora_inicio", "grupo__nombre"]
        verbose_name = "sesión"
        verbose_name_plural = "sesiones"
        constraints = [
            models.UniqueConstraint(fields=["horario", "grupo", "franja"], name="uq_sesion_grupo_franja_en_horario"),
            models.UniqueConstraint(fields=["horario", "asignatura", "grupo", "franja"], name="uq_sesion_asignatura_grupo_franja"),
        ]

    def __str__(self):
        return f"{self.asignatura.nombre} - {self.grupo.nombre} - {self.franja}"

    def clean(self):
        errores = []

        if self.horario_id and self.asignatura_id and self.asignatura.curso_id != self.horario.curso_id:
            errores.append("La asignatura no pertenece al curso del horario.")

        if self.horario_id and self.grupo_id and self.grupo.curso_id != self.horario.curso_id:
            errores.append("El grupo no pertenece al curso del horario.")

        disponibilidad = DisponibilidadProfesor.objects.filter(
            profesor=self.profesor,
            franja=self.franja,
            estado="BLOQUEADO",
        ).first()
        if disponibilidad:
            errores.append("El profesor está marcado como no disponible en esta franja.")

        base = Sesion.objects.filter(
            horario__anio_academico=self.horario.anio_academico,
            horario__semestre=self.horario.semestre,
            franja=self.franja,
        ).exclude(pk=self.pk)

        if base.filter(profesor=self.profesor).exists():
            errores.append("El profesor ya tiene otra sesión en la misma franja.")

        if base.filter(aula=self.aula).exists():
            errores.append("El aula ya está ocupada en la misma franja.")

        if base.filter(grupo=self.grupo).exists():
            errores.append("El grupo ya tiene otra asignatura en la misma franja.")

        if self.asignatura.es_transversal and self.asignatura.codigo_global_compartido:
            otras = Sesion.objects.filter(
                horario__anio_academico=self.horario.anio_academico,
                horario__semestre=self.horario.semestre,
                asignatura__codigo_global_compartido=self.asignatura.codigo_global_compartido,
            ).exclude(asignatura=self.asignatura).exclude(pk=self.pk)
            if otras.exists() and not otras.filter(franja=self.franja).exists():
                errores.append("La asignatura transversal debe mantener la misma franja global en todas sus titulaciones.")

        if errores:
            raise ValidationError({"franja": errores})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PerfilAlumno(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True)
    asignaturas = models.ManyToManyField(Asignatura, blank=True, related_name="alumnos")

    class Meta:
        verbose_name = "perfil de alumno"
        verbose_name_plural = "perfiles de alumnos"

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Notificacion(TimeStampedModel):
    NIVEL_CHOICES = [
        ("INFO", "Informativa"),
        ("SUCCESS", "Éxito"),
        ("WARNING", "Advertencia"),
        ("ERROR", "Error"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones")
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default="INFO")
    titulo = models.CharField(max_length=120)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    url_destino = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.usuario} - {self.titulo}"


class AuditLog(TimeStampedModel):
    ACCION_CHOICES = [
        ("CREATE", "Creación"),
        ("UPDATE", "Actualización"),
        ("DELETE", "Borrado"),
        ("WORKFLOW", "Cambio de estado"),
        ("LOGIN", "Acceso"),
        ("VALIDATION", "Validación"),
        ("REPORT", "Informe"),
        ("GENERATION", "Generación"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    modelo = models.CharField(max_length=80)
    objeto_id = models.CharField(max_length=80, blank=True)
    descripcion = models.TextField()
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self):
        return f"{self.creado:%Y-%m-%d %H:%M} - {self.accion} - {self.modelo}"
