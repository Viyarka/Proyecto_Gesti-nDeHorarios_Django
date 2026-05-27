import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DisponibilidadProfesor, HistorialDisponibilidad, Notificacion, PerfilAlumno, Sesion

logger = logging.getLogger("horarios")


@receiver(post_save, sender=Sesion)
def notificar_cambio_sesion(sender, instance, created, **kwargs):
    """Notificaciones in-app para profesor y alumnado ante altas/cambios de sesión."""
    accion = "creada" if created else "actualizada"
    logger.info("Sesión %s: %s", accion, instance)
    url = instance.horario.get_absolute_url()
    mensaje = (
        f"{instance.asignatura.nombre} ({instance.grupo.nombre}) en {instance.franja} "
        f"ha sido {accion}. Aula: {instance.aula.nombre}."
    )

    if instance.profesor.user:
        Notificacion.objects.create(
            usuario=instance.profesor.user,
            nivel="INFO",
            titulo=f"Sesión {accion}",
            mensaje=mensaje,
            url_destino=url,
        )

    perfiles = PerfilAlumno.objects.filter(asignaturas=instance.asignatura) | PerfilAlumno.objects.filter(grupo=instance.grupo)
    for perfil in perfiles.distinct().select_related("user"):
        Notificacion.objects.create(
            usuario=perfil.user,
            nivel="WARNING" if not created else "INFO",
            titulo=f"Cambio en tu horario",
            mensaje=mensaje,
            url_destino="/alumno/horario/",
        )


@receiver(post_save, sender=DisponibilidadProfesor)
def registrar_historial_disponibilidad(sender, instance, created, **kwargs):
    """Historial simple para cumplir RF-08.2."""
    HistorialDisponibilidad.objects.create(
        profesor=instance.profesor,
        franja=instance.franja,
        estado=instance.estado,
        motivo=instance.motivo,
    )
