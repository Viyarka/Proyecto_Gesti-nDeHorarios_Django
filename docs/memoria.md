# Memoria breve - Sistema de Gestión de Horarios Académicos

Se ha desarrollado una aplicación web en Django para gestionar horarios académicos universitarios. El sistema permite crear, editar, consultar y borrar horarios segmentados por titulación, curso, semestre y año académico. También permite administrar sesiones, profesores, aulas, grupos, asignaturas y franjas horarias.

La parte principal del proyecto es el motor de reglas, implementado en `horarios/models.py` y `horarios/motor.py`. Este motor valida que un profesor no tenga dos clases simultáneas, que un aula no esté ocupada por dos asignaturas a la vez, que un grupo no tenga solapamientos, que se respeten los bloqueos de disponibilidad y que no se dupliquen sesiones de una misma asignatura. Además, se ha añadido una generación global de horarios para planificar todos los cursos de un semestre a la vez, evitando conflictos entre titulaciones.

La aplicación incluye workflow de estados para los horarios: Borrador, Revisión, Aprobado y Rechazado. Antes de aprobar un horario se ejecuta una validación completa, incluyendo el cumplimiento de horas lectivas. También se han incorporado informes dinámicos filtrables y exportables a PDF y Excel, vista personalizada para profesorado, vista de horario para alumnado, validación de matrícula con detección inmediata de solapamientos, notificaciones internas y auditoría.

Para reforzar la calidad del proyecto se han añadido pruebas automáticas en `horarios/tests.py`, que verifican las restricciones principales del dominio, el funcionamiento de la generación global y varias vistas. El proyecto también está preparado para despliegue, incluyendo configuración mediante variables de entorno, `Procfile`, `render.yaml` y documentación para Render y PythonAnywhere.

La arquitectura sigue el patrón MVT de Django: modelos para representar datos y reglas, vistas para procesar peticiones, templates para la interfaz y URLconf para conectar rutas con vistas. La interfaz se ha rediseñado con un panel lateral, tarjetas, tablas más claras y diseño responsive.
