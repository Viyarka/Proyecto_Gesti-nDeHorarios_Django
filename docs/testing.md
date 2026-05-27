# Testing

El proyecto incluye pruebas automáticas en `horarios/tests.py`.

## Ejecutar tests

```bash
python manage.py test horarios
```

## Qué se comprueba

- Un profesor no puede tener dos sesiones en la misma franja.
- Un aula no puede estar ocupada por dos sesiones simultáneas.
- Un grupo no puede tener dos asignaturas a la vez.
- La disponibilidad bloqueada del profesor se respeta.
- La validación detecta horas lectivas incompletas.
- La generación global no duplica sesiones.
- La matrícula detecta solapamientos.
- El dashboard, informes y API responden correctamente.
