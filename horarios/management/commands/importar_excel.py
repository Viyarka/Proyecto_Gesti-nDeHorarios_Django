from pathlib import Path
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Importa el Excel original. Para la entrega se recomienda cargar_demo, que ya usa el CSV extraído del Excel."

    def add_arguments(self, parser):
        parser.add_argument("ruta_excel", nargs="?", default="data/HORARIOS_25_26.xlsx")

    def handle(self, *args, **options):
        ruta = Path(options["ruta_excel"])
        if not ruta.exists():
            self.stderr.write("No se encontró el Excel. Usa: python manage.py cargar_demo")
            return
        self.stdout.write("El proyecto incluye un CSV ya normalizado desde el Excel.")
        self.stdout.write("Ejecutando cargar_demo...")
        call_command("cargar_demo")
