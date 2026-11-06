from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

class Categoria(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    activa = models.BooleanField(default=True)
    def __str__(self): return self.nombre

class Liga(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ACTIVA = "ACTIVA", "Activa"
        CERRADA = "CERRADA", "Cerrada"
    nombre = models.CharField(max_length=150, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR, db_index=True)
    es_principal = models.BooleanField(default=False, db_index=True)
    descripcion = models.TextField(blank=True)
    class Meta:
        ordering = ["-fecha_inicio", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["es_principal"], condition=models.Q(es_principal=True), name="una_liga_principal"),
            models.CheckConstraint(condition=models.Q(es_principal=False) | models.Q(estado="ACTIVA"), name="liga_principal_activa"),
        ]
    def __str__(self): return self.nombre

class Jugador(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        RETIRADO = "RETIRADO", "Retirado"
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="jugadores")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["nombre", "id"]
        constraints = [models.UniqueConstraint(models.functions.Lower("nombre"), name="jugador_nombre_ci_unico")]
    def __str__(self): return self.nombre

class Division(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        CANCELADA = "CANCELADA", "Cancelada"
    liga = models.ForeignKey(Liga, on_delete=models.PROTECT, related_name="divisiones")
    nombre = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVA, db_index=True)
    categorias = models.ManyToManyField(Categoria, through="DivisionCategoria", related_name="divisiones")
    class Meta:
        ordering = ["orden", "nombre", "id"]
        constraints = [
            models.UniqueConstraint(fields=["liga", "nombre"], name="division_nombre_unico_por_liga"),
            models.UniqueConstraint(fields=["liga", "orden"], name="division_orden_unico_por_liga"),
        ]
    def __str__(self): return f"{self.liga} · {self.nombre}"
    def clean(self):
        if self.liga_id and self.liga.estado == Liga.Estado.CERRADA:
            raise ValidationError("Una liga cerrada no admite cambios de divisiones.")
    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)

class DivisionCategoria(models.Model):
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="categorias_permitidas")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="configuraciones_division")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["division", "categoria"], name="categoria_unica_en_division")]
    def clean(self):
        if self.division_id and self.division.liga.estado == Liga.Estado.CERRADA:
            raise ValidationError("Una liga cerrada no admite cambios de categorías.")
        if self.division_id and self.division.estado == Division.Estado.CANCELADA:
            raise ValidationError("Una división cancelada no admite cambios de categorías.")
        if type(self).objects.filter(division__liga_id=self.division.liga_id, categoria_id=self.categoria_id).exclude(pk=self.pk).exists():
            raise ValidationError("La categoría ya pertenece a otra división de esta liga.")
    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        if self.division.liga.estado == Liga.Estado.CERRADA or self.division.inscripciones.filter(categoria=self.categoria).exists():
            raise ValidationError("No se puede quitar una categoría usada o perteneciente a una liga cerrada.")
        return super().delete(*args, **kwargs)

class InscripcionDivision(models.Model):
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="inscripciones")
    jugador = models.ForeignKey(Jugador, on_delete=models.PROTECT, related_name="inscripciones")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="inscripciones_historicas")
    activa = models.BooleanField(default=True, db_index=True)
    inscrito_en = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["division", "jugador"], condition=models.Q(activa=True),
            name="jugador_activo_unico_por_division",
        )]
    def clean(self):
        if self.division_id and self.division.liga.estado == Liga.Estado.CERRADA:
            raise ValidationError("Una liga cerrada no admite cambios de inscripciones.")
        if self.division_id and self.division.estado == Division.Estado.CANCELADA:
            raise ValidationError("Una división cancelada no admite cambios de inscripciones.")
        if self.division_id and self.categoria_id and not DivisionCategoria.objects.filter(division_id=self.division_id, categoria_id=self.categoria_id).exists():
            raise ValidationError("La categoría histórica no está permitida en esta división.")
        if not self.pk and self.jugador_id and self.categoria_id and self.jugador.categoria_id != self.categoria_id:
            raise ValidationError("La categoría histórica debe coincidir con la categoría actual al inscribir.")
    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)
    def __str__(self): return f"{self.jugador} en {self.division}"

class Partido(models.Model):
    class Estado(models.TextChoices):
        TERMINADO = "TERMINADO", "Terminado"
        ANULADO = "ANULADO", "Anulado"
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="partidos")
    fecha = models.DateField()
    jugador_a = models.ForeignKey(InscripcionDivision, on_delete=models.PROTECT, related_name="partidos_como_a")
    jugador_b = models.ForeignKey(InscripcionDivision, on_delete=models.PROTECT, related_name="partidos_como_b")
    set_1 = models.CharField(max_length=7)
    set_2 = models.CharField(max_length=7)
    super_tiebreak = models.CharField(max_length=15, blank=True)
    ganador = models.ForeignKey(InscripcionDivision, on_delete=models.PROTECT, related_name="partidos_ganados", editable=False)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.TERMINADO, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-fecha", "-id"]
        constraints = [models.CheckConstraint(condition=~models.Q(jugador_a=models.F("jugador_b")), name="inscripciones_partido_distintas")]
    def clean(self):
        from .services import validar_partido
        if self.division.liga.estado == Liga.Estado.CERRADA or self.division.estado == Division.Estado.CANCELADA:
            raise ValidationError("La división no está disponible para registrar o modificar partidos.")
        if self.jugador_a.division_id != self.division_id or self.jugador_b.division_id != self.division_id:
            raise ValidationError("Ambos jugadores deben estar inscritos en la división del partido.")
        exigir_activos = True
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).values("jugador_a_id", "jugador_b_id").first()
            exigir_activos = not anterior or anterior["jugador_a_id"] != self.jugador_a_id or anterior["jugador_b_id"] != self.jugador_b_id
        r = validar_partido(self.jugador_a, self.jugador_b, self.set_1, self.set_2, self.super_tiebreak, exigir_activos)
        self.ganador = self.jugador_a if r.ganador == 1 else self.jugador_b
    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)

class Torneo(models.Model):
    liga = models.ForeignKey(Liga, on_delete=models.PROTECT, related_name="torneos")
    nombre = models.CharField(max_length=150)
    fecha = models.DateField()
    descripcion = models.TextField(blank=True)
    anulado = models.BooleanField(default=False, db_index=True)
    class Meta:
        ordering = ["-fecha", "nombre"]
        constraints = [models.UniqueConstraint(fields=["liga", "nombre"], name="torneo_nombre_unico_por_liga")]
    def __str__(self): return self.nombre

class PuntosTorneo(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.PROTECT, related_name="asignaciones")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="puntos_torneo")
    inscripcion = models.ForeignKey(InscripcionDivision, on_delete=models.PROTECT, related_name="puntos_torneo")
    puntos = models.IntegerField()
    anulado = models.BooleanField(default=False, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["torneo", "division", "inscripcion"], name="puntos_unicos_torneo_division_inscripcion"),
            models.CheckConstraint(condition=models.Q(puntos__gte=0), name="puntos_torneo_no_negativos"),
        ]
    def clean(self):
        if self.division_id and self.inscripcion_id and self.inscripcion.division_id != self.division_id:
            raise ValidationError("La inscripción no pertenece a la división indicada.")
        if self.torneo_id and self.division_id and self.torneo.liga_id != self.division.liga_id:
            raise ValidationError("El torneo y la división deben pertenecer a la misma liga.")
        if self.division_id and (self.division.liga.estado == Liga.Estado.CERRADA or self.division.estado == Division.Estado.CANCELADA):
            raise ValidationError("La división no está disponible para asignar puntos.")
    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)

class SnapshotRanking(models.Model):
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="snapshots_ranking")
    generado_en = models.DateTimeField(auto_now_add=True)
    datos = models.JSONField()
    es_final = models.BooleanField(default=False)
    class Meta:
        ordering = ["-generado_en", "-id"]
        constraints = [models.UniqueConstraint(fields=["division"], condition=models.Q(es_final=True), name="un_snapshot_final_por_division")]

class Auditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    accion = models.CharField(max_length=30)
    modelo = models.CharField(max_length=80)
    objeto_id = models.CharField(max_length=80)
    cambios = models.JSONField(default=dict)
    creado_en = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-creado_en", "-id"]
