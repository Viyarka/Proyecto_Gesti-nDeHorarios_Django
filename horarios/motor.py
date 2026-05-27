from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Asignatura, DisponibilidadProfesor, FranjaHoraria, Horario, Sesion

DIAS_ORDEN = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES"]


@dataclass
class ResultadoGeneracion:
    creadas: int = 0
    omitidas: int = 0
    errores: list = field(default_factory=list)

    @property
    def total(self):
        return self.creadas + self.omitidas


def clave_slot(sesion):
    return (sesion.franja.dia, sesion.franja.hora_inicio, sesion.franja.hora_fin)


def validar_horario(horario, exigir_horas=False):
    """Comprueba reglas duras: profesor, aula, grupo, disponibilidad, horas y transversales.

    exigir_horas=True se usa antes de aprobar: las horas lectivas incompletas pasan a error.
    """
    errores = []
    avisos = []

    sesiones = (
        horario.sesiones.select_related("profesor", "aula", "grupo", "franja", "asignatura")
        .order_by("franja__dia", "franja__hora_inicio")
    )

    profesor_slot = defaultdict(list)
    aula_slot = defaultdict(list)
    grupo_slot = defaultdict(list)
    asignatura_slot = defaultdict(list)
    horas_asignatura = defaultdict(float)

    for sesion in sesiones:
        slot = clave_slot(sesion)
        profesor_slot[(sesion.profesor_id, *slot)].append(sesion)
        aula_slot[(sesion.aula_id, *slot)].append(sesion)
        grupo_slot[(sesion.grupo_id, *slot)].append(sesion)
        asignatura_slot[(sesion.asignatura_id, sesion.grupo_id, *slot)].append(sesion)
        horas_asignatura[sesion.asignatura_id] += sesion.franja.duracion_horas

        if DisponibilidadProfesor.objects.filter(
            profesor=sesion.profesor,
            franja=sesion.franja,
            estado="BLOQUEADO",
        ).exists():
            errores.append(f"{sesion.profesor.codigo} no está disponible en {sesion.franja}.")

    for coleccion, texto in [
        (profesor_slot, "Profesor con dos clases a la vez"),
        (aula_slot, "Aula con dos clases a la vez"),
        (grupo_slot, "Grupo con dos asignaturas a la vez"),
        (asignatura_slot, "Sesión duplicada de la misma asignatura"),
    ]:
        for _, items in coleccion.items():
            if len(items) > 1:
                detalle = ", ".join(str(s.asignatura) for s in items)
                errores.append(f"{texto}: {detalle}")

    for asignatura in Asignatura.objects.filter(curso=horario.curso, semestre=horario.semestre):
        objetivo = asignatura.horas_totales_requeridas
        real = horas_asignatura.get(asignatura.id, 0)
        if real < objetivo:
            mensaje = f"{asignatura.nombre}: {real:g}h planificadas de {objetivo:g}h requeridas."
            if exigir_horas:
                errores.append(mensaje)
            else:
                avisos.append(mensaje)
        elif real > objetivo:
            errores.append(f"{asignatura.nombre}: {real:g}h planificadas, supera las {objetivo:g}h requeridas.")

    # Las asignaturas transversales pueden tener varias sesiones semanales.
    # La regla correcta es que todas las titulaciones compartidas mantengan el mismo conjunto de franjas,
    # no que toda la asignatura tenga una única franja.
    for asignatura in Asignatura.objects.filter(
        curso=horario.curso,
        semestre=horario.semestre,
        es_transversal=True,
    ).exclude(codigo_global_compartido=""):
        slots_propios = {clave_slot(s) for s in sesiones.filter(asignatura=asignatura)}
        if not slots_propios:
            continue
        otras_sesiones = Sesion.objects.filter(
            horario__anio_academico=horario.anio_academico,
            horario__semestre=horario.semestre,
            asignatura__codigo_global_compartido=asignatura.codigo_global_compartido,
        ).exclude(asignatura=asignatura).select_related("franja", "asignatura")

        slots_por_asignatura = defaultdict(set)
        for sesion_transversal in otras_sesiones:
            slots_por_asignatura[sesion_transversal.asignatura_id].add(clave_slot(sesion_transversal))

        for slots_otra in slots_por_asignatura.values():
            if slots_otra and slots_otra != slots_propios:
                errores.append(
                    f"Asignatura transversal {asignatura.codigo_global_compartido}: "
                    "no mantiene el mismo conjunto de franjas en todas las titulaciones."
                )
                break

    return {
        "es_valido": not errores,
        "errores": errores,
        "avisos": avisos,
        "total_sesiones": sesiones.count(),
        "horas_ok": not [a for a in avisos if "requeridas" in a] and not [e for e in errores if "requeridas" in e],
    }


def _franjas_ordenadas_para_asignatura(asignatura):
    franjas = list(FranjaHoraria.objects.filter(activa=True))
    orden_dias = {dia: indice for indice, dia in enumerate(DIAS_ORDEN)}
    franjas.sort(key=lambda f: (orden_dias.get(f.dia, 99), f.hora_inicio, f.hora_fin))

    # Regla de dominio: en grados individuales el último año se planifica por la tarde.
    if asignatura.curso.numero >= asignatura.curso.titulacion.duracion_anios and not asignatura.curso.titulacion.permite_manana_tarde:
        franjas = [f for f in franjas if f.es_tarde]

    preferidas = []
    normales = []
    bloqueadas = set(
        DisponibilidadProfesor.objects.filter(
            profesor=asignatura.profesor_titular,
            estado="BLOQUEADO",
        ).values_list("franja_id", flat=True)
    )
    preferencias = set(
        DisponibilidadProfesor.objects.filter(
            profesor=asignatura.profesor_titular,
            estado="PREFERENTE",
        ).values_list("franja_id", flat=True)
    )

    for franja in franjas:
        if franja.id in bloqueadas:
            continue
        if franja.id in preferencias:
            preferidas.append(franja)
        else:
            normales.append(franja)

    return preferidas + normales


def _crear_sesion_si_cabe(horario, asignatura, grupo, franja):
    profesor = asignatura.profesor_titular
    aula = asignatura.aula_preferente
    if not profesor or not aula:
        raise ValidationError("La asignatura no tiene profesor titular o aula preferente.")

    if Sesion.objects.filter(horario=horario, asignatura=asignatura, grupo=grupo, franja=franja).exists():
        raise ValidationError("La sesión ya existe en esa franja.")

    sesion = Sesion(
        horario=horario,
        asignatura=asignatura,
        profesor=profesor,
        aula=aula,
        grupo=grupo,
        franja=franja,
        observaciones="Generada automáticamente por el motor global.",
    )
    sesion.save()
    return sesion


@transaction.atomic
def generar_horario_basico(horario, sobrescribir=False):
    """Genera un único horario con reglas duras y sin duplicar horas."""
    resultado = generar_horarios_globales(
        anio_academico=horario.anio_academico,
        semestre=horario.semestre,
        horarios=[horario],
        sobrescribir=sobrescribir,
    )
    if resultado.errores:
        raise ValidationError("; ".join(resultado.errores[:5]))
    return resultado.creadas


@transaction.atomic
def generar_horarios_globales(anio_academico, semestre, horarios=None, sobrescribir=False):
    """Genera todos los horarios de un semestre a la vez.

    Al crear las sesiones se usa Sesion.clean(), que mira profesor/aula/grupo en todo el año
    académico y semestre. Por eso no permite que un profesor quede solapado entre titulaciones.
    """
    if horarios is None:
        horarios = Horario.objects.filter(anio_academico=anio_academico, semestre=semestre).select_related("curso", "titulacion")
    else:
        horarios = list(horarios)

    if sobrescribir:
        Sesion.objects.filter(horario__in=horarios).delete()

    resultado = ResultadoGeneracion()

    # Primero doble grado si existe, luego grados simples. Así se respeta la jerarquía del documento.
    horarios = sorted(
        horarios,
        key=lambda h: (0 if h.titulacion.permite_manana_tarde else 1, h.titulacion.codigo, h.curso.numero),
    )

    for horario in horarios:
        grupo = horario.curso.grupos.order_by("nombre").first()
        if not grupo:
            resultado.errores.append(f"{horario}: no tiene grupo creado.")
            continue

        asignaturas = (
            Asignatura.objects.filter(curso=horario.curso, semestre=horario.semestre)
            .select_related("profesor_titular", "aula_preferente", "curso", "curso__titulacion")
            .order_by("codigo")
        )

        for asignatura in asignaturas:
            sesiones_actuales = horario.sesiones.filter(asignatura=asignatura, grupo=grupo).count()
            necesarias = max(asignatura.sesiones_semanales - sesiones_actuales, 0)

            for _ in range(necesarias):
                colocada = False
                dias_ya_usados = set(
                    horario.sesiones.filter(asignatura=asignatura, grupo=grupo)
                    .values_list("franja__dia", flat=True)
                )
                franjas_candidatas = _franjas_ordenadas_para_asignatura(asignatura)

                # Primero intentamos repartir una misma asignatura en días distintos.
                # Si no hay hueco, se permite otra franja del mismo día como último recurso.
                franjas_repartidas = [f for f in franjas_candidatas if f.dia not in dias_ya_usados]
                for franja in franjas_repartidas + franjas_candidatas:
                    try:
                        _crear_sesion_si_cabe(horario, asignatura, grupo, franja)
                        resultado.creadas += 1
                        colocada = True
                        break
                    except ValidationError:
                        continue
                if not colocada:
                    resultado.omitidas += 1
                    resultado.errores.append(
                        f"No se pudo colocar {asignatura.nombre} en {horario} sin solapar profesor/aula/grupo."
                    )

    return resultado


def detectar_conflictos_asignaturas(asignaturas: Iterable[Asignatura]):
    """Detecta conflictos inmediatos entre asignaturas seleccionadas en matrícula."""
    sesiones = Sesion.objects.filter(asignatura__in=asignaturas).select_related(
        "asignatura", "grupo", "franja", "profesor", "aula", "horario"
    )

    por_slot = defaultdict(list)
    for sesion in sesiones:
        por_slot[clave_slot(sesion)].append(sesion)

    return [items for items in por_slot.values() if len(items) > 1]


def detectar_conflictos_alumno(perfil_alumno):
    """Detecta solapamientos entre las asignaturas matriculadas por un alumno."""
    return detectar_conflictos_asignaturas(perfil_alumno.asignaturas.all())
