from datetime import time

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    Asignatura,
    Aula,
    Curso,
    DisponibilidadProfesor,
    FranjaHoraria,
    Grupo,
    Horario,
    PerfilAlumno,
    Profesor,
    Sesion,
    Titulacion,
)
from .motor import detectar_conflictos_asignaturas, generar_horarios_globales, validar_horario


class BaseHorarioTest(TestCase):
    def setUp(self):
        self.titulacion = Titulacion.objects.create(nombre="Ingeniería Informática", codigo="INF")
        self.curso = Curso.objects.create(titulacion=self.titulacion, numero=1, nombre="1º INF")
        self.grupo = Grupo.objects.create(nombre="1INF", curso=self.curso, tipo="TEORIA")
        self.profesor = Profesor.objects.create(nombre="Profesor Test", codigo="PT")
        self.profesor2 = Profesor.objects.create(nombre="Profesor Dos", codigo="P2")
        self.aula = Aula.objects.create(nombre="Aula 1")
        self.aula2 = Aula.objects.create(nombre="Aula 2")
        self.asig1 = Asignatura.objects.create(codigo="A1", nombre="Asignatura 1", curso=self.curso, profesor_titular=self.profesor, aula_preferente=self.aula)
        self.asig2 = Asignatura.objects.create(codigo="A2", nombre="Asignatura 2", curso=self.curso, profesor_titular=self.profesor, aula_preferente=self.aula2)
        self.asig3 = Asignatura.objects.create(codigo="A3", nombre="Asignatura 3", curso=self.curso, profesor_titular=self.profesor2, aula_preferente=self.aula2)
        self.franja = FranjaHoraria.objects.create(dia="LUNES", hora_inicio=time(9, 0), hora_fin=time(11, 0))
        self.franja2 = FranjaHoraria.objects.create(dia="MARTES", hora_inicio=time(9, 0), hora_fin=time(11, 0))
        self.franja3 = FranjaHoraria.objects.create(dia="MIÉRCOLES", hora_inicio=time(9, 0), hora_fin=time(11, 0))
        self.franja4 = FranjaHoraria.objects.create(dia="JUEVES", hora_inicio=time(9, 0), hora_fin=time(11, 0))
        self.horario = Horario.objects.create(anio_academico="2025-2026", semestre="1", titulacion=self.titulacion, curso=self.curso)


class MotorReglasTest(BaseHorarioTest):
    def test_profesor_no_puede_tener_dos_sesiones_misma_franja(self):
        Sesion.objects.create(horario=self.horario, asignatura=self.asig1, profesor=self.profesor, aula=self.aula, grupo=self.grupo, franja=self.franja)
        with self.assertRaises(ValidationError):
            Sesion.objects.create(horario=self.horario, asignatura=self.asig2, profesor=self.profesor, aula=self.aula2, grupo=self.grupo, franja=self.franja)

    def test_aula_no_puede_tener_dos_sesiones_misma_franja(self):
        otro_grupo = Grupo.objects.create(nombre="1INF-B", curso=self.curso, tipo="TEORIA")
        Sesion.objects.create(horario=self.horario, asignatura=self.asig1, profesor=self.profesor, aula=self.aula, grupo=self.grupo, franja=self.franja)
        with self.assertRaises(ValidationError):
            Sesion.objects.create(horario=self.horario, asignatura=self.asig3, profesor=self.profesor2, aula=self.aula, grupo=otro_grupo, franja=self.franja)

    def test_grupo_no_puede_tener_dos_sesiones_misma_franja(self):
        Sesion.objects.create(horario=self.horario, asignatura=self.asig1, profesor=self.profesor, aula=self.aula, grupo=self.grupo, franja=self.franja)
        with self.assertRaises(ValidationError):
            Sesion.objects.create(horario=self.horario, asignatura=self.asig3, profesor=self.profesor2, aula=self.aula2, grupo=self.grupo, franja=self.franja)

    def test_respeta_bloqueo_de_disponibilidad(self):
        DisponibilidadProfesor.objects.create(profesor=self.profesor, franja=self.franja, estado="BLOQUEADO")
        with self.assertRaises(ValidationError):
            Sesion.objects.create(horario=self.horario, asignatura=self.asig1, profesor=self.profesor, aula=self.aula, grupo=self.grupo, franja=self.franja)

    def test_validacion_detecta_horas_incompletas_antes_de_aprobar(self):
        resultado = validar_horario(self.horario, exigir_horas=True)
        self.assertFalse(resultado["es_valido"])
        self.assertTrue(any("requeridas" in error for error in resultado["errores"]))

    def test_generacion_global_no_duplica_sesiones(self):
        resultado = generar_horarios_globales("2025-2026", "1", sobrescribir=True)
        self.assertGreater(resultado.creadas, 0)
        primera_cuenta = Sesion.objects.count()
        segundo = generar_horarios_globales("2025-2026", "1", sobrescribir=False)
        self.assertEqual(segundo.creadas, 0)
        self.assertEqual(Sesion.objects.count(), primera_cuenta)


class AlumnoTest(BaseHorarioTest):
    def test_detecta_conflicto_de_matricula(self):
        Sesion.objects.create(horario=self.horario, asignatura=self.asig1, profesor=self.profesor, aula=self.aula, grupo=self.grupo, franja=self.franja)
        otro_grupo = Grupo.objects.create(nombre="1INF-C", curso=self.curso, tipo="TEORIA")
        Sesion.objects.create(horario=self.horario, asignatura=self.asig3, profesor=self.profesor2, aula=self.aula2, grupo=otro_grupo, franja=self.franja)
        conflictos = detectar_conflictos_asignaturas([self.asig1, self.asig3])
        self.assertEqual(len(conflictos), 1)


class VistasTest(BaseHorarioTest):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="decano", password="Decano12345")
        grupo = Group.objects.create(name="Decanato")
        self.user.groups.add(grupo)
        self.client = Client()
        self.client.login(username="decano", password="Decano12345")

    def test_dashboard_responde(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_api_sesiones_devuelve_json(self):
        response = self.client.get(reverse("api_sesiones"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())

    def test_informes_responde(self):
        response = self.client.get(reverse("informes"))
        self.assertEqual(response.status_code, 200)
