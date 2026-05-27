# Generated manually for final delivery

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("horarios", "0002_historialdisponibilidad_profesorsuplente_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="asignatura",
            name="semestre",
            field=models.CharField(choices=[("1", "Primer semestre"), ("2", "Segundo semestre")], default="1", max_length=1),
        ),
    ]
