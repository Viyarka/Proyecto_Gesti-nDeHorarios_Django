from django.apps import AppConfig


class HorariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horarios"

    def ready(self):
        import horarios.signals  # noqa: F401
