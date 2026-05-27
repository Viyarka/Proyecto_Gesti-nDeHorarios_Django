import csv
from datetime import datetime, time
from pathlib import Path

from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from horarios.models import (
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
from horarios.motor import generar_horarios_globales


class Command(BaseCommand):
    help = "Carga usuarios, roles y una demo realista de horarios académicos."

    def add_arguments(self, parser):
        parser.add_argument("--csv", default="data/horarios_iniciales.csv")
        parser.add_argument(
            "--usar-csv",
            action="store_true",
            help="Carga el CSV original en lugar de la demo realista generada.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra los datos académicos anteriores antes de cargar la demo.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.crear_roles_y_usuarios()

        if options["reset"]:
            self.reset_demo()

        if options["usar_csv"]:
            csv_path = self.resolver_csv_path(options["csv"])
            sesiones_creadas, conflictos_omitidos = self.importar_csv(csv_path)
        else:
            sesiones_creadas, conflictos_omitidos = self.crear_demo_realista()

        self.stdout.write(
            self.style.SUCCESS(
                f"Datos de demo cargados. Sesiones creadas: {sesiones_creadas}. "
                f"Conflictos omitidos: {conflictos_omitidos}."
            )
        )

    def reset_demo(self):
        """Limpia los datos académicos de la demo para evitar duplicidades de ejecuciones anteriores."""
        Notificacion.objects.all().delete()
        AuditLog.objects.all().delete()
        PerfilAlumno.objects.all().delete()
        Sesion.objects.all().delete()
        ProfesorSuplente.objects.all().delete()
        HistorialDisponibilidad.objects.all().delete()
        DisponibilidadProfesor.objects.all().delete()
        Asignatura.objects.all().delete()
        Horario.objects.all().delete()
        Grupo.objects.all().delete()
        Curso.objects.all().delete()
        Titulacion.objects.all().delete()
        Aula.objects.all().delete()
        Profesor.objects.all().delete()
        FranjaHoraria.objects.all().delete()
        self.stdout.write(self.style.WARNING("Datos académicos anteriores eliminados."))

    def crear_roles_y_usuarios(self):
        roles = {
            "Decanato": [
                "add_horario",
                "change_horario",
                "delete_horario",
                "add_sesion",
                "change_sesion",
                "delete_sesion",
                "view_auditlog",
            ],
            "Profesorado": [
                "view_horario",
                "view_sesion",
                "add_disponibilidadprofesor",
                "change_disponibilidadprofesor",
                "view_historialdisponibilidad",
            ],
            "Alumnado": ["view_horario", "view_sesion"],
            "IT": ["view_auditlog", "view_horario", "view_sesion", "view_historialdisponibilidad"],
        }

        for nombre, permisos in roles.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            for codename in permisos:
                permiso = Permission.objects.filter(codename=codename).first()
                if permiso:
                    grupo.permissions.add(permiso)

        usuarios = [
            ("decano", "Decano12345", "Decanato", True),
            ("profesor", "Profesor12345", "Profesorado", False),
            ("alumno", "Alumno12345", "Alumnado", False),
            ("it", "ITusuario12345", "IT", True),
        ]

        for username, password, grupo_nombre, staff in usuarios:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@ucjc.local", "is_staff": staff},
            )
            if created:
                user.set_password(password)
                user.save()
            elif staff and not user.is_staff:
                user.is_staff = True
                user.save(update_fields=["is_staff"])

            user.groups.add(Group.objects.get(name=grupo_nombre))

    def crear_demo_realista(self):
        """Crea una demo completa y coherente: 5 asignaturas por semestre y 2 sesiones por asignatura.

        Resultado esperado:
        - Grados simples: 10 sesiones semanales por horario.
        - Doble grado: 12 sesiones semanales por horario, al tener una asignatura extra.
        - Robótica incluye 1º, 2º, 3º y 4º.
        - Las sesiones se generan de forma global para evitar solapes de profesor, aula y grupo.
        """
        self.crear_franjas_base()

        planes = [
            ("Ingeniería Informática", "INF", 4, False),
            ("Ingeniería Robótica", "ROB", 4, False),
            ("Ingeniería Telemática", "TEL", 4, False),
            ("Doble Grado Informática + Robótica", "DOBLE", 5, True),
        ]

        for nombre, codigo, duracion, permite_manana_tarde in planes:
            titulacion, _ = Titulacion.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "codigo": codigo,
                    "duracion_anios": duracion,
                    "permite_manana_tarde": permite_manana_tarde,
                },
            )

            for numero_curso in range(1, duracion + 1):
                curso, _ = Curso.objects.get_or_create(
                    titulacion=titulacion,
                    numero=numero_curso,
                    defaults={"nombre": f"{numero_curso}º {codigo}"},
                )
                grupo, _ = Grupo.objects.get_or_create(
                    nombre=f"{numero_curso}{codigo}",
                    defaults={"curso": curso, "tipo": "TEORIA"},
                )
                if grupo.curso_id != curso.id:
                    grupo.curso = curso
                    grupo.save(update_fields=["curso"])

                Aula.objects.get_or_create(nombre=f"Aula {grupo.nombre}", defaults={"capacidad": 45})

                for semestre in ["1", "2"]:
                    Horario.objects.get_or_create(
                        anio_academico="2025-2026",
                        semestre=semestre,
                        titulacion=titulacion,
                        curso=curso,
                        defaults={"estado": "BORRADOR"},
                    )

                    for indice, nombre_asignatura in enumerate(self.nombres_asignaturas(codigo, numero_curso, semestre), start=1):
                        profesor = self.get_profesor_realista(codigo, numero_curso, semestre, indice)
                        aula = Aula.objects.get(nombre=f"Aula {grupo.nombre}")
                        es_transversal = nombre_asignatura == "Fundamentos de Programación"
                        codigo_global = "" if not es_transversal else "TRANS-" + "".join(ch for ch in nombre_asignatura.upper() if ch.isalnum())

                        Asignatura.objects.update_or_create(
                            codigo=f"{codigo}-{numero_curso}-S{semestre}-{indice:02d}",
                            defaults={
                                "nombre": nombre_asignatura,
                                "curso": curso,
                                "semestre": semestre,
                                "profesor_titular": profesor,
                                "aula_preferente": aula,
                                "sesiones_semanales": 2,
                                "horas_por_sesion": 2,
                                "es_transversal": es_transversal,
                                "codigo_global_compartido": codigo_global,
                            },
                        )

        self.crear_disponibilidades_demo()
        total_creadas = 0
        total_omitidas = 0
        for semestre in ["1", "2"]:
            resultado = generar_horarios_globales("2025-2026", semestre, sobrescribir=True)
            total_creadas += resultado.creadas
            total_omitidas += resultado.omitidas
            for error in resultado.errores[:10]:
                self.stdout.write(self.style.WARNING(error))

        self.crear_suplentes_demo()
        self.crear_perfil_alumno_demo()
        self.vincular_profesor_demo_a_usuario()
        return total_creadas, total_omitidas

    def crear_franjas_base(self):
        franjas = [
            (time(9, 0), time(11, 0)),
            (time(11, 0), time(13, 0)),
            (time(13, 0), time(15, 0)),
            (time(15, 30), time(17, 30)),
            (time(17, 30), time(19, 30)),
            (time(19, 30), time(21, 30)),
        ]
        for dia in ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES"]:
            for inicio, fin in franjas:
                FranjaHoraria.objects.get_or_create(
                    dia=dia,
                    hora_inicio=inicio,
                    hora_fin=fin,
                    defaults={"etiqueta": f"{inicio:%H:%M}-{fin:%H:%M}", "activa": True},
                )

    def nombres_asignaturas(self, codigo, curso, semestre):
        base = {
            "INF": {
                (1, "1"): ["Fundamentos de Programación", "Matemática Discreta", "Fundamentos Físicos", "Empresa y Gestión", "Tecnología de Computadores"],
                (1, "2"): ["Programación", "Álgebra Lineal", "Estructura de Computadores", "Sistemas Operativos", "Bases de Datos I"],
                (2, "1"): ["Estructuras de Datos", "Estadística", "Arquitectura de Computadores", "Ingeniería del Software I", "Redes de Computadores"],
                (2, "2"): ["Bases de Datos II", "Redes y Sistemas Web", "Programación Avanzada", "Sistemas Distribuidos", "Interacción Persona Ordenador"],
                (3, "1"): ["Administración de Sistemas", "Seguridad Informática", "Inteligencia Artificial", "Desarrollo de Aplicaciones", "Gestión de Proyectos"],
                (3, "2"): ["Aprendizaje Automático", "Desarrollo de Software Avanzado", "DevOps", "Calidad del Software", "Computación en la Nube"],
                (4, "1"): ["Arquitecturas Software", "Ciberseguridad", "Minería de Datos", "Sistemas Empresariales", "Proyecto Integrado I"],
                (4, "2"): ["Auditoría Informática", "Aplicaciones en Red", "Ingeniería de Datos", "Proyecto Integrado II", "Trabajo Fin de Grado"],
            },
            "ROB": {
                (1, "1"): ["Fundamentos de Programación", "Matemáticas para Robótica", "Física para Robótica", "Electrónica Básica", "Expresión Gráfica"],
                (1, "2"): ["Programación Robótica", "Álgebra Lineal", "Mecánica", "Sistemas Operativos", "Sensores y Actuadores"],
                (2, "1"): ["Automática", "Modelado de Robots", "Electrónica Digital", "Control Industrial", "Redes Industriales"],
                (2, "2"): ["Arquitectura de Computadores", "Bases de Datos", "Visión Artificial", "Control de Robots", "Sistemas Embebidos"],
                (3, "1"): ["Robótica Móvil", "Sistemas Distribuidos", "Planificación de Trayectorias", "Simulación Robótica", "Diseño Mecatrónico"],
                (3, "2"): ["Robots Cooperativos", "Aprendizaje Automático", "Percepción Robótica", "Integración de Sistemas", "Laboratorio de Robótica"],
                (4, "1"): ["Robótica Autónoma", "Ciberfísica", "Control Avanzado", "Proyecto Robótico I", "Ética y Legislación Tecnológica"],
                (4, "2"): ["Robótica Colaborativa", "Sistemas Inteligentes", "Mantenimiento Predictivo", "Proyecto Robótico II", "Trabajo Fin de Grado"],
            },
            "TEL": {
                (1, "1"): ["Fundamentos de Programación", "Matemáticas para Telemática", "Fundamentos Físicos", "Electrónica", "Empresa Tecnológica"],
                (1, "2"): ["Programación", "Álgebra Lineal", "Sistemas Digitales", "Fundamentos de Redes", "Bases de Datos"],
                (2, "1"): ["Redes de Comunicaciones", "Señales y Sistemas", "Arquitectura de Internet", "Estadística", "Servicios Telemáticos"],
                (2, "2"): ["Redes Inalámbricas", "Protocolos de Internet", "Seguridad en Redes", "Sistemas Distribuidos", "Aplicaciones Web"],
                (3, "1"): ["Administración de Redes", "Comunicaciones Móviles", "Ciberseguridad", "Cloud Networking", "Gestión de Servicios TI"],
                (3, "2"): ["Redes Definidas por Software", "Internet de las Cosas", "DevOps", "Monitorización de Redes", "Arquitecturas Telemáticas"],
                (4, "1"): ["Ingeniería de Tráfico", "Seguridad Avanzada", "Proyecto Telemático I", "Sistemas 5G", "Auditoría de Redes"],
                (4, "2"): ["Servicios Cloud", "Redes Corporativas", "Proyecto Telemático II", "Continuidad de Servicio", "Trabajo Fin de Grado"],
            },
            "DOBLE": {},
        }

        if codigo == "DOBLE":
            comunes = [
                "Fundamentos de Programación",
                "Matemáticas Aplicadas",
                "Sistemas Inteligentes",
                "Robótica y Software",
                "Gestión de Proyectos Tecnológicos",
                "Laboratorio Integrado",
            ]
            return [f"{nombre} {curso}.{semestre}" if nombre not in {"Fundamentos de Programación"} else nombre for nombre in comunes]

        return base[codigo][(curso, semestre)]

    def get_profesor_realista(self, codigo, curso, semestre, indice):
        nombres = [
            "Ana Saha", "Diego Millán", "Celia García", "Rafael Montúfar", "Iván Sosa",
            "César Andrés", "David Baños", "Lino González", "Marta Bravo", "Daniel Sampedro",
            "Javier Martínez", "Laura Pérez", "Elena Ruiz", "Carlos Medina", "Sofía Torres",
        ]
        nombre = nombres[(curso * 3 + int(semestre) + indice) % len(nombres)]
        codigo_profesor = f"P{codigo}{curso}{semestre}{indice:02d}"
        profesor, _ = Profesor.objects.get_or_create(
            codigo=codigo_profesor,
            defaults={
                "nombre": nombre,
                "area_conocimiento": "Ingeniería",
                "email": f"{codigo_profesor.lower()}@ucjc.local",
            },
        )
        return profesor

    def crear_disponibilidades_demo(self):
        # Se deja constancia de preferencias y bloqueos para demostrar que el motor las tiene en cuenta.
        primera_franja = FranjaHoraria.objects.filter(dia="LUNES", hora_inicio=time(9, 0)).first()
        preferente = FranjaHoraria.objects.filter(dia="MARTES", hora_inicio=time(11, 0)).first()
        for profesor in Profesor.objects.all():
            if primera_franja and profesor.codigo.endswith("05"):
                DisponibilidadProfesor.objects.get_or_create(
                    profesor=profesor,
                    franja=primera_franja,
                    defaults={"estado": "BLOQUEADO", "motivo": "Bloqueo de ejemplo para validación"},
                )
            if preferente and profesor.codigo.endswith("01"):
                DisponibilidadProfesor.objects.get_or_create(
                    profesor=profesor,
                    franja=preferente,
                    defaults={"estado": "PREFERENTE", "motivo": "Preferencia de ejemplo"},
                )

    def crear_suplentes_demo(self):
        profesores = list(Profesor.objects.all()[:12])
        if not profesores:
            return
        for i, asignatura in enumerate(Asignatura.objects.select_related("profesor_titular")[:30]):
            suplente = profesores[i % len(profesores)]
            if suplente != asignatura.profesor_titular:
                ProfesorSuplente.objects.get_or_create(
                    asignatura=asignatura,
                    profesor=suplente,
                    defaults={
                        "area_conocimiento": asignatura.profesor_titular.area_conocimiento if asignatura.profesor_titular else "Ingeniería",
                        "prioridad": 1,
                    },
                )

    def crear_perfil_alumno_demo(self):
        alumno = User.objects.filter(username="alumno").first()
        grupo = Grupo.objects.filter(nombre="1INF").first()
        if alumno and grupo:
            perfil, _ = PerfilAlumno.objects.get_or_create(
                user=alumno,
                defaults={"grupo": grupo},
            )
            if perfil.grupo_id != grupo.id:
                perfil.grupo = grupo
                perfil.save(update_fields=["grupo"])
            perfil.asignaturas.set(Asignatura.objects.filter(curso=grupo.curso, semestre="1")[:5])

    def vincular_profesor_demo_a_usuario(self):
        user = User.objects.filter(username="profesor").first()
        profesor = Profesor.objects.order_by("codigo").first()
        if user and profesor:
            Profesor.objects.filter(user=user).update(user=None)
            profesor.user = user
            profesor.save(update_fields=["user"])

    # Modo alternativo: conserva la importación desde CSV original por si se quiere comparar con el Excel base.
    def resolver_csv_path(self, csv_option):
        csv_option = Path(csv_option)
        if csv_option.is_absolute() and csv_option.exists():
            return csv_option
        command_file = Path(__file__).resolve()
        project_dir = command_file.parents[3]
        parent_dir = project_dir.parent
        candidates = [Path.cwd() / csv_option, project_dir / csv_option, parent_dir / csv_option]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError("No se encontró el CSV de horarios.")

    def importar_csv(self, csv_path):
        sesiones_creadas = 0
        conflictos_omitidos = 0
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not self.fila_valida(row):
                    continue
                titulacion = self.get_titulacion(row)
                curso, _ = Curso.objects.get_or_create(
                    titulacion=titulacion,
                    numero=int(row["curso"]),
                    defaults={"nombre": f"{row['curso']}º {titulacion.codigo}"},
                )
                grupo, _ = Grupo.objects.get_or_create(
                    nombre=row["grupo"],
                    defaults={"curso": curso, "tipo": row["tipo_grupo"]},
                )
                aula, _ = Aula.objects.get_or_create(nombre=row["aula"], defaults={"capacidad": 40})
                profesor = self.get_profesor_csv(row)
                asignatura, _ = Asignatura.objects.get_or_create(
                    codigo=self.codigo_asignatura(row),
                    defaults={
                        "nombre": row["asignatura"],
                        "curso": curso,
                        "semestre": row["semestre"],
                        "profesor_titular": profesor,
                        "aula_preferente": aula,
                        "sesiones_semanales": 2,
                        "horas_por_sesion": 2,
                    },
                )
                franja, _ = FranjaHoraria.objects.get_or_create(
                    dia=row["dia"],
                    hora_inicio=datetime.strptime(row["hora_inicio"], "%H:%M").time(),
                    hora_fin=datetime.strptime(row["hora_fin"], "%H:%M").time(),
                    defaults={"etiqueta": f"{row['hora_inicio']}-{row['hora_fin']}"},
                )
                Horario.objects.get_or_create(
                    anio_academico=row["anio_academico"],
                    semestre=row["semestre"],
                    titulacion=titulacion,
                    curso=curso,
                    defaults={"estado": "BORRADOR"},
                )
                horario = Horario.objects.get(anio_academico=row["anio_academico"], semestre=row["semestre"], titulacion=titulacion, curso=curso)
                try:
                    _, created = Sesion.objects.get_or_create(
                        horario=horario,
                        asignatura=asignatura,
                        profesor=profesor,
                        aula=aula,
                        grupo=grupo,
                        franja=franja,
                        defaults={"observaciones": row.get("celda_original", "")},
                    )
                    if created:
                        sesiones_creadas += 1
                except ValidationError:
                    conflictos_omitidos += 1
        self.crear_suplentes_demo()
        self.crear_perfil_alumno_demo()
        return sesiones_creadas, conflictos_omitidos

    def fila_valida(self, row):
        campos = ["titulacion", "curso", "grupo", "tipo_grupo", "aula", "profesor_codigo", "profesor_nombre", "asignatura", "dia", "hora_inicio", "hora_fin", "anio_academico", "semestre"]
        return all(row.get(campo, "").strip() for campo in campos)

    def get_profesor_csv(self, row):
        profesor_codigo = row["profesor_codigo"].strip() or "PORASIGNAR"
        if profesor_codigo == "PORASIGNAR":
            profesor_codigo = f"PORASIGNAR-{row['grupo']}-{self.codigo_asignatura(row)}"
            profesor_nombre = f"Profesor por asignar {row['grupo']}"
        else:
            profesor_nombre = row["profesor_nombre"]
        profesor, _ = Profesor.objects.get_or_create(
            codigo=profesor_codigo,
            defaults={"nombre": profesor_nombre, "area_conocimiento": "Ingeniería"},
        )
        return profesor

    def get_titulacion(self, row):
        nombre = row["titulacion"]
        codigo = {
            "Ingeniería Informática": "INF",
            "Ingeniería Robótica": "ROB",
            "Ingeniería Telemática": "TEL",
            "Doble Grado Informática + Robótica": "DOBLE",
        }.get(nombre, "GEN")
        duracion = 5 if "Doble" in nombre else 4
        permite_manana_tarde = "Doble" in nombre
        titulacion, _ = Titulacion.objects.get_or_create(
            nombre=nombre,
            defaults={"codigo": codigo, "duracion_anios": duracion, "permite_manana_tarde": permite_manana_tarde},
        )
        return titulacion

    def codigo_asignatura(self, row):
        limpio = "".join(ch for ch in row["asignatura"].upper() if ch.isalnum())[:18]
        return f"{row['semestre']}-{row['grupo']}-{limpio}"
