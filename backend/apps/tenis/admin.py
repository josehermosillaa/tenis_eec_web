from django.contrib import admin
from .models import (Auditoria, Categoria, Division, DivisionCategoria, InscripcionDivision,
                     Jugador, Liga, Partido, PuntosTorneo, SnapshotRanking, Torneo)

admin.site.register([Liga, Categoria, Division, DivisionCategoria, Jugador, InscripcionDivision,
                     Partido, Torneo, PuntosTorneo, SnapshotRanking, Auditoria])
