# Sistema de Gestión de Horarios Académicos - UCJC

Proyecto Django para la asignatura **Desarrollo de Software Avanzado**. La aplicación gestiona horarios académicos universitarios, tomando como referencia el documento de requisitos del sistema y el Excel de horarios iniciales.

## Mejoras de la versión final

Esta versión final añade tres apartados pedidos para la entrega:

1. **Cumplimiento reforzado de requisitos funcionales**: se cubren RF-01 a RF-14 mediante CRUD, motor de reglas, informes, workflow, disponibilidad, vistas de profesor/alumno, avisos y validación de matrícula.
2. **Testing añadido**: el archivo `horarios/tests.py` contiene pruebas automáticas del motor de reglas, generación global, vistas principales y API JSON.
3. **Preparación para despliegue**: se incluyen `Procfile`, `render.yaml`, configuración por variables de entorno y guías para Render/PythonAnywhere.

## Funcionalidades principales

- Gestión CRUD de horarios por titulación, curso, semestre y año académico.
- Motor de reglas para evitar solapes:
  - un profesor no puede impartir dos sesiones en la misma franja;
  - un aula no puede estar ocupada por dos sesiones simultáneas;
  - un grupo no puede tener dos asignaturas al mismo tiempo;
  - se respetan bloqueos de disponibilidad del profesor;
  - no se duplican sesiones de la misma asignatura en el mismo slot.
- Generación global de todos los horarios de un semestre, respetando la disponibilidad docente entre titulaciones y evitando duplicidades de sesiones.
- Workflow: **Borrador -> Revisión -> Aprobado/Rechazado**.
- Validación de horas lectivas antes de aprobar.
- Configuración dinámica de franjas horarias.
- Gestión de disponibilidad del profesorado: disponible, preferente o bloqueado.
- Historial de cambios de disponibilidad.
- Profesores titulares y suplentes por área de conocimiento.
- Vista personalizada de carga docente.
- Vista de horario de alumnado.
- Validación de matrícula con detección inmediata de solapamientos.
- Notificaciones in-app para cambios de sesiones.
- Auditoría de acciones relevantes.
- Informes dinámicos filtrables y exportables a Excel/PDF.
- API JSON: `/api/sesiones/`.
- Interfaz visual mejorada y responsive.
- Tabla de horarios corregida para mostrar cada franja una sola vez.
- Excel y PDF exportados con cabeceras, estilos y mejor presentación.

## Instalación local en Visual Studio Code

Desde la carpeta donde está `manage.py`:

```bash
python -m venv .venv
```

En Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

Si la `.venv` está en la carpeta anterior, como en algunas entregas:

```bash
..\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

Preparar base de datos:

```bash
python manage.py migrate
python manage.py cargar_demo --reset
python manage.py runserver
```

La opción `--reset` borra la demo anterior y genera una demo coherente desde cero. En esta versión, los grados simples tienen 10 sesiones semanales por horario, el Doble Grado tiene 12 sesiones semanales y Robótica aparece completa de 1º a 4º.

Abrir:

```text
http://127.0.0.1:8000/
```

## Usuarios de prueba

| Rol | Usuario | Contraseña |
|---|---|---|
| Decanato | `decano` | `Decano12345` |
| Profesor | `profesor` | `Profesor12345` |
| Alumno | `alumno` | `Alumno12345` |
| IT | `it` | `ITusuario12345` |

## Testing

Ejecutar todas las pruebas:

```bash
python manage.py test horarios
```

El proyecto incluye pruebas para:

- conflicto de profesor en la misma franja;
- conflicto de aula;
- conflicto de grupo;
- bloqueo de disponibilidad del profesor;
- validación de horas lectivas;
- generación global sin duplicar sesiones;
- detección de conflictos de matrícula;
- dashboard, informes y API JSON.

## Despliegue en Render

El proyecto incluye `render.yaml` y `Procfile`.

Pasos generales:

1. Subir el repositorio a GitHub.
2. En Render, crear un nuevo **Web Service** desde el repositorio.
3. Usar estos comandos:
   - Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - Start: `gunicorn gestion_horarios.wsgi:application`
4. Añadir variables de entorno:
   - `DEBUG=False`
   - `SECRET_KEY=<clave-secreta>`
   - `ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1`
   - `CSRF_TRUSTED_ORIGINS=https://*.onrender.com`

## Despliegue en PythonAnywhere

También se puede desplegar en PythonAnywhere:

1. Subir el proyecto o clonarlo desde GitHub.
2. Crear virtualenv e instalar `requirements.txt`.
3. Configurar una Web App tipo Django.
4. Apuntar el archivo WSGI a `gestion_horarios/wsgi.py`.
5. Configurar static files:
   - URL: `/static/`
   - Carpeta: `.../gestion de horarios/staticfiles`
6. Ejecutar:

```bash
python manage.py collectstatic
python manage.py migrate
python manage.py cargar_demo --reset
```

## Relación con requisitos funcionales

| Requisito | Implementación |
|---|---|
| RF-01 | CRUD de horarios segmentado por titulación, curso, semestre y año académico. |
| RF-02 | `Sesion.clean()` y `motor.py` validan profesor sin solapes. |
| RF-02.1 | `validar_horario(..., exigir_horas=True)` controla horas antes de aprobar. |
| RF-03 | Vista `/informes/` con filtros dinámicos. |
| RF-03.1 | Exportación a Excel y PDF. |
| RF-04 | Estados BORRADOR, REVISION, APROBADO y RECHAZADO. |
| RF-05 | Gestión de franjas horarias desde configuración. |
| RF-05.1 | El motor usa las franjas activas guardadas en base de datos. |
| RF-06 | Modelo `ProfesorSuplente` vinculado a asignaturas por área. |
| RF-07 | Edición manual de sesiones desde vistas y admin. |
| RF-08 | Formulario de disponibilidad docente. |
| RF-08.1 | Estados PREFERENTE, DISPONIBLE y BLOQUEADO. |
| RF-08.2 | Modelo `HistorialDisponibilidad`. |
| RF-09 | Vista `/profesor/carga/`. |
| RF-09.1 | Muestra código, asignatura, aula y franja. |
| RF-09.2 | Muestra grupo/subgrupo. |
| RF-10 | Señales y notificaciones al modificar sesiones. |
| RF-10.1 | Avisos in-app en `/notificaciones/`. |
| RF-11 | Vista `/alumno/horario/`. |
| RF-11.1 | Se filtra por perfil, grupo y curso. |
| RF-11.2 | Horario asociado al plan/titulación. |
| RF-11.3 | Segmentación por grupo y tipo de grupo. |
| RF-12 | Notificaciones para alumnado. |
| RF-12.1 | Detección de conflictos en matrícula. |
| RF-12.2 | Avisos ante cambios de aula, horario o profesor. |
| RF-12.3 | Implementado como notificación in-app; correo queda opcional. |
| RF-13 | Etiqueta visual `Transversal`. |
| RF-14 | Motor de conflictos inter-niveles en matrícula. |
| RF-14.1 | Alerta inmediata antes de guardar matrícula. |

## Estructura importante

```text
gestion_horarios/       Configuración global del proyecto Django
horarios/models.py      Modelos principales y reglas de validación
horarios/views.py       Vistas web
horarios/urls.py        Rutas de la aplicación
horarios/forms.py       Formularios
horarios/motor.py       Motor de validación y generación global
horarios/tests.py       Pruebas automáticas
data/horarios_iniciales.csv  Datos normalizados del Excel
docs/                   Guías de defensa, despliegue y requisitos
```

## Autor

Pablo Villarquide  
Asignatura: Desarrollo de Software Avanzado
