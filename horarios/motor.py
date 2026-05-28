import random
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
    """Devuelve franjas disponibles para una asignatura.

    Para que la demo sea más realista, el motor trabaja con un máximo de tres
    bloques por día. En los cursos normales usa los bloques de mañana
    09:00-11:00, 11:00-13:00 y 13:00-15:00. En último curso de grados simples
    se mantienen tres bloques de tarde para respetar la restricción de dominio
    de planificación por la tarde.
    """
    franjas = list(FranjaHoraria.objects.filter(activa=True))
    orden_dias = {dia: indice for indice, dia in enumerate(DIAS_ORDEN)}
    franjas.sort(key=lambda f: (orden_dias.get(f.dia, 99), f.hora_inicio, f.hora_fin))

    es_ultimo_curso_individual = (
        asignatura.curso.numero >= asignatura.curso.titulacion.duracion_anios
        and not asignatura.curso.titulacion.permite_manana_tarde
    )

    if es_ultimo_curso_individual:
        horas_permitidas = {(15, 30), (17, 30), (19, 30)}
    else:
        horas_permitidas = {(9, 0), (11, 0), (13, 0)}

    franjas = [
        f for f in franjas
        if (f.hora_inicio.hour, f.hora_inicio.minute) in horas_permitidas
    ]

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


def _slots_transversales_existentes(anio_academico, semestre, codigo_global):
    if not codigo_global:
        return []
    sesiones = (
        Sesion.objects.filter(
            horario__anio_academico=anio_academico,
            horario__semestre=semestre,
            asignatura__codigo_global_compartido=codigo_global,
        )
        .select_related("franja")
        .order_by("franja__dia", "franja__hora_inicio")
    )
    franjas = []
    vistos = set()
    for sesion in sesiones:
        clave = (sesion.franja.dia, sesion.franja.hora_inicio, sesion.franja.hora_fin)
        if clave not in vistos:
            vistos.add(clave)
            franjas.append(sesion.franja)
    return franjas


def _elegir_dia_libre(total_sesiones, dias_obligados=None):
    dias_obligados = set(dias_obligados or [])
    candidatos = [dia for dia in DIAS_ORDEN if dia not in dias_obligados]
    if not candidatos:
        return None
    # Para 10 sesiones se consigue una distribución tipo 3-3-2-2-0.
    # Para 12 sesiones se consigue 3-3-3-3-0.
    return random.choice(candidatos)


def _ordenar_candidatas_por_reparto(franjas, dia_libre, conteo_por_dia, dias_asignatura, slots_usados):
    candidatas = []
    for franja in franjas:
        clave = (franja.dia, franja.hora_inicio, franja.hora_fin)
        if clave in slots_usados:
            continue
        if dia_libre and franja.dia == dia_libre:
            continue
        if conteo_por_dia[franja.dia] >= 3:
            continue
        candidatas.append(franja)

    # Primera pasada: no repetir la misma asignatura en el mismo día.
    sin_repetir_dia = [f for f in candidatas if f.dia not in dias_asignatura]
    if sin_repetir_dia:
        candidatas = sin_repetir_dia

    # Priorizamos días con menos clases para que no aparezcan 5 clases en lunes/martes.
    # El componente random hace que cada generación global pueda variar.
    random.shuffle(candidatas)
    candidatas.sort(key=lambda f: (conteo_por_dia[f.dia], DIAS_ORDEN.index(f.dia)))
    return candidatas


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

    Reglas aplicadas en la generación:
    - máximo 3 clases por día en cada horario;
    - se intenta dejar 1 día libre por horario;
    - las sesiones se reparten por toda la semana;
    - una misma asignatura no se coloca dos veces en el mismo día;
    - se respeta disponibilidad/bloqueos del profesorado;
    - las asignaturas transversales mantienen las mismas franjas globales.
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

    plan_transversales = {}

    for horario in horarios:
        # Si no se pide sobrescribir y el horario ya tiene sesiones, no intentamos
        # completarlo para evitar duplicados o mezclas de generaciones anteriores.
        if not sobrescribir and horario.sesiones.exists():
            continue

        grupo = horario.curso.grupos.order_by("nombre").first()
        if not grupo:
            resultado.errores.append(f"{horario}: no tiene grupo creado.")
            continue

        asignaturas = list(
            Asignatura.objects.filter(curso=horario.curso, semestre=horario.semestre)
            .select_related("profesor_titular", "aula_preferente", "curso", "curso__titulacion")
            .order_by("-es_transversal", "codigo")
        )

        total_objetivo = sum(a.sesiones_semanales for a in asignaturas)
        conteo_por_dia = defaultdict(int)
        slots_usados = set()

        for sesion in horario.sesiones.select_related("franja"):
            conteo_por_dia[sesion.franja.dia] += 1
            slots_usados.add((sesion.franja.dia, sesion.franja.hora_inicio, sesion.franja.hora_fin))

        dias_obligados = set()
        for asignatura in asignaturas:
            if asignatura.es_transversal and asignatura.codigo_global_compartido:
                clave_global = (anio_academico, semestre, asignatura.codigo_global_compartido)
                franjas_globales = plan_transversales.get(clave_global) or _slots_transversales_existentes(
                    anio_academico, semestre, asignatura.codigo_global_compartido
                )
                dias_obligados.update(f.dia for f in franjas_globales)

        dia_libre = _elegir_dia_libre(total_objetivo, dias_obligados=dias_obligados)

        for asignatura in asignaturas:
            sesiones_actuales = horario.sesiones.filter(asignatura=asignatura, grupo=grupo).count()
            necesarias = max(asignatura.sesiones_semanales - sesiones_actuales, 0)
            if necesarias <= 0:
                continue

            franjas_fijas = []
            clave_global = None
            if asignatura.es_transversal and asignatura.codigo_global_compartido:
                clave_global = (anio_academico, semestre, asignatura.codigo_global_compartido)
                franjas_fijas = plan_transversales.get(clave_global) or _slots_transversales_existentes(
                    anio_academico, semestre, asignatura.codigo_global_compartido
                )
                franjas_fijas = franjas_fijas[:asignatura.sesiones_semanales]

            creadas_asignatura = []
            dias_ya_usados = set(
                horario.sesiones.filter(asignatura=asignatura, grupo=grupo)
                .values_list("franja__dia", flat=True)
            )

            # Si es transversal y ya existe un plan global, se reutilizan esas franjas.
            for franja in franjas_fijas:
                if len(creadas_asignatura) >= necesarias:
                    break
                try:
                    _crear_sesion_si_cabe(horario, asignatura, grupo, franja)
                    resultado.creadas += 1
                    creadas_asignatura.append(franja)
                    dias_ya_usados.add(franja.dia)
                    conteo_por_dia[franja.dia] += 1
                    slots_usados.add((franja.dia, franja.hora_inicio, franja.hora_fin))
                except ValidationError:
                    continue

            while len(creadas_asignatura) < necesarias:
                franjas_candidatas = _franjas_ordenadas_para_asignatura(asignatura)
                candidatas = _ordenar_candidatas_por_reparto(
                    franjas_candidatas,
                    dia_libre,
                    conteo_por_dia,
                    dias_ya_usados,
                    slots_usados,
                )

                colocada = False
                for franja in candidatas:
                    try:
                        _crear_sesion_si_cabe(horario, asignatura, grupo, franja)
                        resultado.creadas += 1
                        creadas_asignatura.append(franja)
                        dias_ya_usados.add(franja.dia)
                        conteo_por_dia[franja.dia] += 1
                        slots_usados.add((franja.dia, franja.hora_inicio, franja.hora_fin))
                        colocada = True
                        break
                    except ValidationError:
                        continue

                if not colocada:
                    resultado.omitidas += 1
                    resultado.errores.append(
                        f"No se pudo colocar {asignatura.nombre} en {horario} sin solapar profesor/aula/grupo."
                    )
                    break

            if clave_global and clave_global not in plan_transversales:
                franjas_creadas = list(
                    horario.sesiones.filter(asignatura=asignatura, grupo=grupo)
                    .select_related("franja")
                    .order_by("franja__dia", "franja__hora_inicio")
                )
                plan_transversales[clave_global] = [s.franja for s in franjas_creadas]

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
