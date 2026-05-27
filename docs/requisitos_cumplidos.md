# Requisitos cubiertos en la versión final

## Requisitos funcionales

- **RF-01**: CRUD de horarios mediante vistas, formularios y admin.
- **RF-02**: motor de reglas en `Sesion.clean()` y `motor.py`.
- **RF-02.1**: validación de horas requeridas antes de aprobar.
- **RF-03**: informes dinámicos en `/informes/`.
- **RF-03.1**: exportación a PDF y Excel.
- **RF-04**: workflow de estados.
- **RF-05 y RF-05.1**: franjas horarias configurables usadas por el motor.
- **RF-06**: profesores titulares y suplentes.
- **RF-07**: edición manual de sesiones.
- **RF-08, RF-08.1 y RF-08.2**: disponibilidad docente e historial.
- **RF-09, RF-09.1 y RF-09.2**: carga docente con código, aula, franja y grupo.
- **RF-10 y RF-10.1**: notificaciones in-app ante cambios.
- **RF-11, RF-11.1, RF-11.2 y RF-11.3**: vista de horario de alumno con filtros por perfil/grupo.
- **RF-12, RF-12.1, RF-12.2 y RF-12.3**: alertas de cambios y conflictos mediante interfaz web.
- **RF-13**: etiqueta visual de asignaturas transversales.
- **RF-14 y RF-14.1**: validación inmediata de matrícula.

## Requisitos no funcionales trabajados

- **RNF-01/RNF-02**: consultas optimizadas con `select_related` y generación greedy eficiente.
- **RNF-04**: autenticación de Django con contraseñas cifradas.
- **RNF-06/RNF-14**: auditoría y logging.
- **RNF-07**: RBAC mediante grupos de Django.
- **RNF-08/RNF-08.1/RNF-09/RNF-10**: interfaz más clara, responsive y con mensajes semánticos.
- **RNF-12**: endpoint JSON `/api/sesiones/`.
- **RNF-13**: arquitectura Modelo-Vista-Template.
- **RNF-15/RNF-16**: datos configurables, no hardcodeados.
- **RNF-17/RNF-18/RNF-19**: preparación para despliegue y copias con instrucciones de plataforma.

## Testing

Ejecutar:

```bash
python manage.py test horarios
```

Se validan reglas críticas del dominio y vistas principales.


## Ajustes finales tras la presentación

- La carga de demo se ha normalizado para que los grados simples tengan 10 sesiones semanales por horario y el Doble Grado 12.
- Robótica se genera completa de 1º a 4º en ambos semestres.
- La vista de detalle ya no duplica filas de la misma franja horaria.
- El dashboard muestra solo horarios abiertos por el usuario durante la sesión actual.
- Las exportaciones Excel y PDF se han mejorado con cabeceras, estilos y recuento de sesiones.
