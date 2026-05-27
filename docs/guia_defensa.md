# Guía rápida de defensa

## Qué es Django
Django es un framework web de Python. Permite crear aplicaciones con base de datos, rutas, vistas, plantillas, formularios, autenticación y panel de administración.

## Qué es MVT
MVT significa Modelo-Vista-Template:
- Modelo: define datos y reglas de negocio.
- Vista: recibe la petición HTTP y decide qué devolver.
- Template: HTML que se muestra al usuario.

## Dónde está cada cosa en este proyecto
- `models.py`: entidades como Profesor, Asignatura, Horario y Sesion.
- `views.py`: lógica de pantallas.
- `urls.py`: rutas.
- `forms.py`: formularios.
- `motor.py`: validación y generación.
- `templates/`: interfaz HTML.
- `admin.py`: administración de datos.

## Qué hace el motor de reglas
Comprueba que:
- no haya profesor duplicado en la misma franja;
- no haya aula duplicada en la misma franja;
- no haya grupo duplicado en la misma franja;
- el profesor no esté bloqueado por disponibilidad.

## Por qué hay roles
Para cumplir RBAC:
- Decanato gestiona y aprueba horarios.
- Profesorado consulta carga y disponibilidad.
- Alumnado consulta horario.
- IT ve auditoría.

## Qué técnica del tutorial MDN se ha usado
Se ha seguido una estructura similar al tutorial LocalLibrary:
- creación de proyecto y app;
- modelos de base de datos;
- admin de Django;
- vistas y plantillas;
- URLs;
- autenticación;
- formularios;
- exportación y funciones extra adaptadas al problema.
