# Guía de despliegue

## Opción A: Render

1. Subir el proyecto a GitHub.
2. Entrar en Render y crear un Web Service.
3. Seleccionar el repositorio.
4. Build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

5. Start command:

```bash
gunicorn gestion_horarios.wsgi:application
```

6. Variables de entorno:

```text
DEBUG=False
SECRET_KEY=una-clave-secreta-larga
ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
```

## Opción B: PythonAnywhere

1. Subir el proyecto o clonar desde GitHub.
2. Crear virtualenv.
3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Crear Web App de Django.
5. En el archivo WSGI, apuntar a `gestion_horarios.settings`.
6. Configurar static files:

```text
/static/ -> /ruta/al/proyecto/staticfiles
```

7. Ejecutar:

```bash
python manage.py collectstatic
python manage.py migrate
python manage.py cargar_demo --reset
```

## Nota

En local se usa SQLite. Para producción se puede mantener SQLite en demos pequeñas o usar PostgreSQL configurando `DATABASE_URL`.
