from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import transaction

from apps.tenis.models import Liga


class Command(BaseCommand):
    help = "Carga los datos de demostración únicamente cuando no existen ligas."

    def handle(self, *args, **options):
        if Liga.objects.exists():
            self.stdout.write("Datos de demostración omitidos: la base ya contiene ligas.")
            return

        fixture = Path(settings.BASE_DIR) / "demo_data.json"
        if not fixture.exists():
            self.stdout.write(self.style.WARNING("Datos de demostración omitidos: no existe el fixture."))
            return

        with transaction.atomic():
            call_command("loaddata", str(fixture), verbosity=1)
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados."))
