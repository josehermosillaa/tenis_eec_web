from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase
from apps.tenis.models import (Auditoria, Categoria, Division, DivisionCategoria, InscripcionDivision,
    Jugador, Liga, Partido, PuntosTorneo, SnapshotRanking, Torneo)
from apps.tenis.services import (calcular_ranking, cerrar_liga, configurar_categorias_division,
    establecer_liga_principal, inscribir_jugador, validar_set_normal, validar_super_tiebreak)

class DominioDivisionesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.c3 = Categoria.objects.create(nombre="Tercera")
        cls.c4 = Categoria.objects.create(nombre="Cuarta")
        cls.liga = Liga.objects.create(nombre="Invierno 2027", fecha_inicio=date(2027, 6, 1), estado=Liga.Estado.ACTIVA, es_principal=True)
        cls.div = Division.objects.create(liga=cls.liga, nombre="Tercera-Cuarta", orden=1)
        DivisionCategoria.objects.create(division=cls.div, categoria=cls.c3)
        DivisionCategoria.objects.create(division=cls.div, categoria=cls.c4)
        cls.a = Jugador.objects.create(nombre="Ana", categoria=cls.c3)
        cls.b = Jugador.objects.create(nombre="Beto", categoria=cls.c4)
        cls.ia = InscripcionDivision.objects.create(division=cls.div, jugador=cls.a, categoria=cls.c3)
        cls.ib = InscripcionDivision.objects.create(division=cls.div, jugador=cls.b, categoria=cls.c4)

    def test_reglas_de_sets(self):
        for valor in ("6/0", "0-6", "7/5", "6/7"): validar_set_normal(valor)
        for valor in ("6/5", "8/6", "6/6"):
            with self.assertRaises(ValidationError): validar_set_normal(valor)
        for valor in ("10/0", "10/8", "9/11", "14/12"): validar_super_tiebreak(valor)
        for valor in ("10/9", "11/8", "12/9"):
            with self.assertRaises(ValidationError): validar_super_tiebreak(valor)

    def test_partido_entre_categorias_y_ranking_de_division(self):
        p = Partido.objects.create(division=self.div, fecha=date.today(), jugador_a=self.ia, jugador_b=self.ib,
            set_1="6/4", set_2="3/6", super_tiebreak="10/8", ganador=self.ia)
        self.assertEqual(p.ganador, self.ia)
        ranking = {x["jugador"]: x for x in calcular_ranking(self.div)}
        self.assertEqual(ranking[self.a]["puntos_partidos"], 3)
        self.assertEqual(ranking[self.b]["puntos_partidos"], 2)
        self.assertEqual(ranking[self.a]["juegos_ganados"], 9)

    def test_retiro_oculta_jugador_y_reactivacion_recupera_historial(self):
        Partido.objects.create(division=self.div, fecha=date.today(), jugador_a=self.ia, jugador_b=self.ib,
            set_1="6/4", set_2="6/3", ganador=self.ia)
        self.a.estado = Jugador.Estado.RETIRADO; self.a.save()
        ranking = calcular_ranking(self.div)
        self.assertEqual([fila["jugador"] for fila in ranking], [self.b])
        self.assertEqual(ranking[0]["puntos_partidos"], 1)
        self.a.estado = Jugador.Estado.ACTIVO; self.a.save()
        restaurado = calcular_ranking(self.div)
        self.assertEqual(restaurado[0]["jugador"], self.a)
        self.assertEqual(restaurado[0]["puntos_partidos"], 3)

    def test_rankings_de_divisiones_son_independientes(self):
        otra_liga = Liga.objects.create(nombre="Verano 2028", fecha_inicio=date(2028, 1, 1), estado=Liga.Estado.ACTIVA)
        otra = Division.objects.create(liga=otra_liga, nombre="Tercera-Cuarta", orden=1)
        DivisionCategoria.objects.create(division=otra, categoria=self.c3)
        otra_i = InscripcionDivision.objects.create(division=otra, jugador=self.a, categoria=self.c3)
        torneo = Torneo.objects.create(liga=otra_liga, nombre="Apertura", fecha=date.today())
        PuntosTorneo.objects.create(torneo=torneo, division=otra, inscripcion=otra_i, puntos=20)
        self.assertEqual(calcular_ranking(self.div)[0]["puntos_totales"], 0)
        self.assertEqual(calcular_ranking(otra)[0]["puntos_totales"], 20)

    def test_categoria_no_se_repite_entre_divisiones_de_liga(self):
        otra = Division.objects.create(liga=self.liga, nombre="Otra", orden=2)
        with self.assertRaises(ValidationError): DivisionCategoria.objects.create(division=otra, categoria=self.c3)

    def test_rechaza_inscripcion_en_categoria_no_permitida(self):
        honor = Categoria.objects.create(nombre="Honor")
        j = Jugador.objects.create(nombre="Carla", categoria=honor)
        with self.assertRaises(ValidationError): InscripcionDivision.objects.create(division=self.div, jugador=j, categoria=honor)

    def test_partido_rechaza_inscrito_de_otra_division(self):
        otra_liga = Liga.objects.create(nombre="Liga B", fecha_inicio=date.today(), estado=Liga.Estado.ACTIVA)
        otra = Division.objects.create(liga=otra_liga, nombre="Cuarta", orden=1)
        DivisionCategoria.objects.create(division=otra, categoria=self.c4)
        otro_i = InscripcionDivision.objects.create(division=otra, jugador=self.b, categoria=self.c4)
        with self.assertRaises(ValidationError):
            Partido.objects.create(division=self.div, fecha=date.today(), jugador_a=self.ia, jugador_b=otro_i,
                set_1="6/0", set_2="6/0", ganador=self.ia)

    def test_liga_cerrada_bloquea_resultados(self):
        self.liga.estado = Liga.Estado.CERRADA; self.liga.es_principal = False; self.liga.save()
        with self.assertRaises(ValidationError):
            Partido.objects.create(division=self.div, fecha=date.today(), jugador_a=self.ia, jugador_b=self.ib,
                set_1="6/0", set_2="6/0", ganador=self.ia)

    def test_configuracion_transaccional_no_quita_categoria_usada(self):
        with self.assertRaises(ValidationError):
            configurar_categorias_division(self.div, [self.c4])
        self.assertEqual(self.div.categorias.count(), 2)

    def test_servicio_inscribe_y_conserva_categoria_historica(self):
        jugador = Jugador.objects.create(nombre="Carla", categoria=self.c3)
        inscripcion = inscribir_jugador(self.div, jugador)
        jugador.categoria = self.c4; jugador.save()
        inscripcion.refresh_from_db()
        self.assertEqual(inscripcion.categoria, self.c3)
        self.assertTrue(Auditoria.objects.filter(accion="INSCRIBIR", objeto_id=str(inscripcion.pk)).exists())
        with self.assertRaises(ValidationError): inscribir_jugador(self.div, jugador)

    def test_cambiar_liga_principal(self):
        nueva = Liga.objects.create(nombre="Liga Nueva", fecha_inicio=date.today(), estado=Liga.Estado.ACTIVA)
        establecer_liga_principal(nueva)
        self.liga.refresh_from_db(); nueva.refresh_from_db()
        self.assertFalse(self.liga.es_principal)
        self.assertTrue(nueva.es_principal)
        borrador = Liga.objects.create(nombre="Borrador", fecha_inicio=date.today())
        with self.assertRaises(ValidationError): establecer_liga_principal(borrador)

    def test_cierre_genera_snapshot_final_y_bloquea_liga(self):
        Partido.objects.create(division=self.div, fecha=date.today(), jugador_a=self.ia, jugador_b=self.ib,
            set_1="6/0", set_2="6/0", ganador=self.ia)
        snapshots = cerrar_liga(self.liga)
        self.liga.refresh_from_db()
        self.assertEqual(self.liga.estado, Liga.Estado.CERRADA)
        self.assertFalse(self.liga.es_principal)
        self.assertIsNotNone(self.liga.fecha_fin)
        self.assertEqual(len(snapshots), 1)
        snapshot = SnapshotRanking.objects.get(division=self.div, es_final=True)
        self.assertEqual(snapshot.datos[0]["jugador"], "Ana")
        self.assertEqual(snapshot.datos[0]["puntos_totales"], 3)
        self.assertTrue(Auditoria.objects.filter(accion="CERRAR_LIGA").exists())
        with self.assertRaises(ValidationError): cerrar_liga(self.liga)

    def test_cierre_es_atomico_si_una_division_no_esta_configurada(self):
        Division.objects.create(liga=self.liga, nombre="Sin configurar", orden=2)
        with self.assertRaises(ValidationError): cerrar_liga(self.liga)
        self.liga.refresh_from_db()
        self.assertEqual(self.liga.estado, Liga.Estado.ACTIVA)
        self.assertFalse(SnapshotRanking.objects.exists())
