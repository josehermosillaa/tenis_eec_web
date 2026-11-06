import re
from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import (Auditoria, Categoria, Division, DivisionCategoria, InscripcionDivision,
                     Jugador, Liga, Partido, PuntosTorneo, SnapshotRanking)

PATRON = re.compile(r"^(\d+)\s*[/-]\s*(\d+)$")
SETS_VALIDOS = {(6, i) for i in range(5)} | {(7, 5), (7, 6)}

def _parsear(valor):
    match = PATRON.fullmatch((valor or "").strip())
    if not match: raise ValidationError("Formato inválido; usa n/n o n-n.")
    return tuple(map(int, match.groups()))

def validar_set_normal(valor):
    juegos = _parsear(valor)
    if juegos not in SETS_VALIDOS and juegos[::-1] not in SETS_VALIDOS: raise ValidationError("Resultado de set normal inválido.")
    return juegos

def validar_super_tiebreak(valor):
    a, b = _parsear(valor); mayor, diferencia = max(a, b), abs(a - b)
    if not ((mayor == 10 and diferencia >= 2) or (mayor > 10 and diferencia == 2)):
        raise ValidationError("Super Tiebreak inválido: a 10, con diferencia mínima de dos.")
    return a, b

@dataclass(frozen=True)
class ResultadoPartido:
    ganador: int
    sets: tuple
    super_tiebreak: tuple | None

def validar_partido(a, b, set_1, set_2, super_tiebreak=""):
    if a.pk == b.pk: raise ValidationError("Un jugador no puede competir contra sí mismo.")
    if a.division_id != b.division_id: raise ValidationError("Las inscripciones deben pertenecer a la misma división.")
    if not a.activa or not b.activa: raise ValidationError("Solo inscripciones activas pueden disputar partidos nuevos.")
    if a.jugador.estado != Jugador.Estado.ACTIVO or b.jugador.estado != Jugador.Estado.ACTIVO:
        raise ValidationError("Solo jugadores activos pueden disputar partidos nuevos.")
    sets = (validar_set_normal(set_1), validar_set_normal(set_2))
    ganadores = tuple(1 if x > y else 2 for x, y in sets)
    if ganadores[0] == ganadores[1]:
        if super_tiebreak: raise ValidationError("No corresponde Super Tiebreak tras dos sets del mismo jugador.")
        return ResultadoPartido(ganadores[0], sets, None)
    if not super_tiebreak: raise ValidationError("El Super Tiebreak es obligatorio con un set por jugador.")
    st = validar_super_tiebreak(super_tiebreak)
    return ResultadoPartido(1 if st[0] > st[1] else 2, sets, st)

def calcular_ranking(division):
    stats = {}
    for i in InscripcionDivision.objects.filter(division=division).select_related("jugador", "categoria"):
        stats[i.pk] = {"inscripcion": i, "jugador": i.jugador, "categoria": i.categoria, "puntos_partidos": 0,
            "puntos_torneos": 0, "partidos": 0, "ganados": 0, "perdidos": 0, "sets_ganados": 0,
            "sets_perdidos": 0, "juegos_ganados": 0, "juegos_perdidos": 0}
    for p in Partido.objects.filter(division=division, estado=Partido.Estado.TERMINADO):
        a, b = stats[p.jugador_a_id], stats[p.jugador_b_id]
        a["partidos"] += 1; b["partidos"] += 1
        g, perdedor = (a, b) if p.ganador_id == p.jugador_a_id else (b, a)
        g["ganados"] += 1; perdedor["perdidos"] += 1
        g["puntos_partidos"] += 3; perdedor["puntos_partidos"] += 2 if p.super_tiebreak else 1
        for ja, jb in (validar_set_normal(p.set_1), validar_set_normal(p.set_2)):
            a["juegos_ganados"] += ja; a["juegos_perdidos"] += jb
            b["juegos_ganados"] += jb; b["juegos_perdidos"] += ja
            gs, ps = (a, b) if ja > jb else (b, a); gs["sets_ganados"] += 1; ps["sets_perdidos"] += 1
        if p.super_tiebreak:
            sa, sb = validar_super_tiebreak(p.super_tiebreak)
            gs, ps = (a, b) if sa > sb else (b, a); gs["sets_ganados"] += 1; ps["sets_perdidos"] += 1
    for pt in PuntosTorneo.objects.filter(division=division, anulado=False, torneo__anulado=False):
        stats[pt.inscripcion_id]["puntos_torneos"] += pt.puntos
    filas = []
    for s in stats.values():
        if not s["inscripcion"].activa or s["jugador"].estado != Jugador.Estado.ACTIVO: continue
        s["diferencia_sets"] = s["sets_ganados"] - s["sets_perdidos"]
        s["diferencia_juegos"] = s["juegos_ganados"] - s["juegos_perdidos"]
        s["puntos_totales"] = s["puntos_partidos"] + s["puntos_torneos"]
        filas.append(s)
    filas.sort(key=lambda s: (-s["puntos_totales"], -s["diferencia_sets"], -s["diferencia_juegos"], -s["juegos_ganados"], s["jugador"].nombre.casefold()))
    for posicion, s in enumerate(filas, 1): s["posicion"] = posicion
    return filas

def _auditar(usuario, accion, objeto, cambios):
    return Auditoria.objects.create(usuario=usuario, accion=accion, modelo=objeto._meta.label,
                                     objeto_id=str(objeto.pk), cambios=cambios)

def _ranking_serializable(division):
    campos = ("posicion", "puntos_partidos", "puntos_torneos", "puntos_totales", "partidos",
              "ganados", "perdidos", "sets_ganados", "sets_perdidos", "diferencia_sets",
              "juegos_ganados", "juegos_perdidos", "diferencia_juegos")
    return [{
        "inscripcion_id": fila["inscripcion"].pk,
        "jugador_id": fila["jugador"].pk,
        "jugador": fila["jugador"].nombre,
        "categoria_id": fila["categoria"].pk,
        "categoria": fila["categoria"].nombre,
        **{campo: fila[campo] for campo in campos},
    } for fila in calcular_ranking(division)]

@transaction.atomic
def configurar_categorias_division(division, categorias, usuario=None):
    division = Division.objects.select_for_update().select_related("liga").get(pk=division.pk)
    if division.liga.estado == Liga.Estado.CERRADA:
        raise ValidationError("Una liga cerrada no admite cambios de categorías.")
    ids = [categoria.pk for categoria in categorias]
    if not ids: raise ValidationError("Una división debe tener al menos una categoría permitida.")
    if len(ids) != len(set(ids)): raise ValidationError("No se pueden repetir categorías en la configuración.")
    if Categoria.objects.filter(pk__in=ids).count() != len(ids): raise ValidationError("Existe una categoría inválida.")
    conflictos = DivisionCategoria.objects.filter(
        division__liga=division.liga, categoria_id__in=ids
    ).exclude(division=division)
    if conflictos.exists(): raise ValidationError("Una categoría ya pertenece a otra división de esta liga.")
    actuales = {rel.categoria_id: rel for rel in division.categorias_permitidas.select_for_update()}
    quitar = set(actuales) - set(ids)
    usadas = set(division.inscripciones.filter(categoria_id__in=quitar).values_list("categoria_id", flat=True))
    if usadas: raise ValidationError("No se puede quitar una categoría con inscripciones existentes.")
    for categoria_id in quitar: actuales[categoria_id].delete()
    for categoria_id in set(ids) - set(actuales):
        DivisionCategoria.objects.create(division=division, categoria_id=categoria_id)
    _auditar(usuario, "CONFIGURAR_CATEGORIAS", division, {"categorias": ids})
    return division

@transaction.atomic
def inscribir_jugador(division, jugador, usuario=None):
    division = Division.objects.select_for_update().select_related("liga").get(pk=division.pk)
    jugador = Jugador.objects.select_for_update().select_related("categoria").get(pk=jugador.pk)
    if division.liga.estado == Liga.Estado.CERRADA: raise ValidationError("La liga está cerrada.")
    if jugador.estado != Jugador.Estado.ACTIVO: raise ValidationError("Solo se pueden inscribir jugadores activos.")
    if not division.categorias_permitidas.exists(): raise ValidationError("La división no tiene categorías configuradas.")
    if not DivisionCategoria.objects.filter(division=division, categoria=jugador.categoria).exists():
        raise ValidationError("La categoría del jugador no está permitida en esta división.")
    if InscripcionDivision.objects.filter(division=division, jugador=jugador).exists():
        raise ValidationError("El jugador ya está inscrito en esta división.")
    inscripcion = InscripcionDivision.objects.create(
        division=division, jugador=jugador, categoria=jugador.categoria
    )
    _auditar(usuario, "INSCRIBIR", inscripcion, {"categoria_historica_id": jugador.categoria_id})
    return inscripcion

@transaction.atomic
def establecer_liga_principal(liga, usuario=None):
    liga = Liga.objects.select_for_update().get(pk=liga.pk)
    if liga.estado != Liga.Estado.ACTIVA: raise ValidationError("Solo una liga activa puede ser principal.")
    Liga.objects.select_for_update().filter(es_principal=True).exclude(pk=liga.pk).update(es_principal=False)
    if not liga.es_principal:
        liga.es_principal = True
        liga.save(update_fields=["es_principal"])
    _auditar(usuario, "ESTABLECER_PRINCIPAL", liga, {"es_principal": True})
    return liga

@transaction.atomic
def cerrar_liga(liga, usuario=None):
    liga = Liga.objects.select_for_update().get(pk=liga.pk)
    if liga.estado != Liga.Estado.ACTIVA: raise ValidationError("Solo se puede cerrar una liga activa.")
    divisiones = list(Division.objects.select_for_update().filter(liga=liga).order_by("orden", "id"))
    if not divisiones: raise ValidationError("La liga debe tener al menos una división.")
    for division in divisiones:
        if not division.categorias_permitidas.exists():
            raise ValidationError(f"La división {division.nombre} no tiene categorías permitidas.")
        if SnapshotRanking.objects.filter(division=division, es_final=True).exists():
            raise ValidationError("Ya existe un snapshot final para una división de esta liga.")
    snapshots = [SnapshotRanking.objects.create(
        division=division, datos=_ranking_serializable(division), es_final=True
    ) for division in divisiones]
    liga.estado = Liga.Estado.CERRADA
    liga.es_principal = False
    if not liga.fecha_fin: liga.fecha_fin = timezone.localdate()
    liga.save(update_fields=["estado", "es_principal", "fecha_fin"])
    _auditar(usuario, "CERRAR_LIGA", liga, {"snapshots": [s.pk for s in snapshots]})
    return snapshots
