from datetime import date
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APITestCase
from apps.tenis.models import Categoria, Division, DivisionCategoria, InscripcionDivision, Jugador, Liga, Partido

class ApiTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nombre="Tercera")
        cls.liga = Liga.objects.create(nombre="Liga API", fecha_inicio=date.today(), estado=Liga.Estado.ACTIVA, es_principal=True)
        cls.division = Division.objects.create(liga=cls.liga, nombre="Tercera", orden=1)
        DivisionCategoria.objects.create(division=cls.division, categoria=cls.categoria)
        cls.jugador = Jugador.objects.create(nombre="Ana API", categoria=cls.categoria)
        cls.inscripcion = InscripcionDivision.objects.create(division=cls.division, jugador=cls.jugador, categoria=cls.categoria)
        cls.admin = get_user_model().objects.create_user(username="admin", password="secreto", is_staff=True)
        cls.normal = get_user_model().objects.create_user(username="normal", password="secreto")

    def test_endpoints_publicos_sin_autenticacion(self):
        for url in ("/api/ligas/principal/", f"/api/ligas/{self.liga.pk}/divisiones/",
                    f"/api/divisiones/{self.division.pk}/ranking/",
                    f"/api/divisiones/{self.division.pk}/partidos/",
                    f"/api/divisiones/{self.division.pk}/jugadores/", "/api/jugadores/",
                    f"/api/jugadores/{self.jugador.pk}/", f"/api/jugadores/{self.jugador.pk}/partidos/",
                    "/api/partidos/", "/api/torneos/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_perfil_publico_incluye_competencia_y_estadisticas(self):
        respuesta = self.client.get(f"/api/jugadores/{self.jugador.pk}/perfil/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["jugador"]["id"], self.jugador.pk)
        self.assertEqual(respuesta.data["liga"]["id"], self.liga.pk)
        self.assertEqual(respuesta.data["division"]["id"], self.division.pk)
        self.assertEqual(respuesta.data["estadisticas"]["posicion"], 1)
        self.assertEqual(respuesta.data["ranking"][0]["jugador_id"], self.jugador.pk)

    def test_endpoints_admin_rechazan_anonimo_y_no_staff(self):
        self.assertIn(self.client.post("/api/admin/ligas/", {}).status_code, (401, 403))
        self.client.force_authenticate(self.normal)
        self.assertEqual(self.client.post("/api/admin/ligas/", {}).status_code, 403)

    def test_administrador_puede_inscribir_por_servicio(self):
        jugador = Jugador.objects.create(nombre="Beto API", categoria=self.categoria)
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(f"/api/admin/divisiones/{self.division.pk}/inscripciones/", {"jugador": jugador.pk})
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(respuesta.data["categoria"], self.categoria.pk)

    def test_solo_elimina_division_vacia_de_liga_principal_activa(self):
        categoria = Categoria.objects.create(nombre="Cuarta")
        vacia = Division.objects.create(liga=self.liga, nombre="Cuarta", orden=2)
        DivisionCategoria.objects.create(division=vacia, categoria=categoria)
        self.client.force_authenticate(self.admin)
        eliminada = self.client.delete(f"/api/admin/divisiones/{vacia.pk}/")
        self.assertEqual(eliminada.status_code, 204)
        self.assertFalse(Division.objects.filter(pk=vacia.pk).exists())

        solo_inactivos = Division.objects.create(liga=self.liga, nombre="Cuarta inactiva", orden=2)
        DivisionCategoria.objects.create(division=solo_inactivos, categoria=categoria)
        jugador_inactivo = Jugador.objects.create(nombre="Jugador retirado de división", categoria=categoria)
        InscripcionDivision.objects.create(
            division=solo_inactivos, jugador=jugador_inactivo, categoria=categoria, activa=False
        )
        eliminada_con_inactivos = self.client.delete(f"/api/admin/divisiones/{solo_inactivos.pk}/")
        self.assertEqual(eliminada_con_inactivos.status_code, 204)
        self.assertFalse(Division.objects.filter(pk=solo_inactivos.pk).exists())

        con_inscritos = self.client.delete(f"/api/admin/divisiones/{self.division.pk}/")
        self.assertEqual(con_inscritos.status_code, 400)
        self.assertTrue(Division.objects.filter(pk=self.division.pk).exists())

        liga_borrador = Liga.objects.create(nombre="Liga futura", fecha_inicio=date.today())
        division_borrador = Division.objects.create(liga=liga_borrador, nombre="Futura", orden=1)
        no_activa = self.client.delete(f"/api/admin/divisiones/{division_borrador.pk}/")
        self.assertEqual(no_activa.status_code, 400)

    def test_editar_orden_division_desplaza_las_demas(self):
        categoria_dos = Categoria.objects.create(nombre="Segunda")
        categoria_uno = Categoria.objects.create(nombre="Primera")
        segunda = Division.objects.create(liga=self.liga, nombre="Segunda", orden=2)
        primera = Division.objects.create(liga=self.liga, nombre="Primera", orden=3)
        DivisionCategoria.objects.create(division=segunda, categoria=categoria_dos)
        DivisionCategoria.objects.create(division=primera, categoria=categoria_uno)
        self.client.force_authenticate(self.admin)
        respuesta = self.client.patch(f"/api/admin/divisiones/{primera.pk}/", {
            "nombre": "Primera editada", "orden": 1, "categorias": [categoria_uno.pk]
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.division.refresh_from_db(); segunda.refresh_from_db(); primera.refresh_from_db()
        self.assertEqual((primera.orden, self.division.orden, segunda.orden), (1, 2, 3))
        self.assertEqual(primera.nombre, "Primera editada")

    def test_cancelar_division_oculta_y_bloquea_hasta_reactivarla(self):
        self.client.force_authenticate(self.admin)
        cancelada = self.client.post(f"/api/admin/divisiones/{self.division.pk}/cancelar/")
        self.assertEqual(cancelada.status_code, 200, cancelada.data)
        self.assertEqual(cancelada.data["estado"], Division.Estado.CANCELADA)
        publicas = self.client.get(f"/api/ligas/{self.liga.pk}/divisiones/").data
        self.assertNotIn(self.division.pk, [division["id"] for division in publicas])
        jugador = Jugador.objects.create(nombre="Jugador bloqueado", categoria=self.categoria)
        bloqueada = self.client.post(
            f"/api/admin/divisiones/{self.division.pk}/inscripciones/", {"jugador": jugador.pk}
        )
        self.assertEqual(bloqueada.status_code, 400)

        reactivada = self.client.post(f"/api/admin/divisiones/{self.division.pk}/reactivar/")
        self.assertEqual(reactivada.status_code, 200, reactivada.data)
        self.assertEqual(reactivada.data["estado"], Division.Estado.ACTIVA)
        publicas = self.client.get(f"/api/ligas/{self.liga.pk}/divisiones/").data
        self.assertIn(self.division.pk, [division["id"] for division in publicas])

    def test_categoria_incompatible_retorna_error_json_400(self):
        otra_categoria = Categoria.objects.create(nombre="Segunda")
        jugador = Jugador.objects.create(nombre="Jugador incompatible", categoria=otra_categoria)
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(
            f"/api/admin/divisiones/{self.division.pk}/inscripciones/", {"jugador": jugador.pk}
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertIn("categoría", str(respuesta.data).lower())

    def test_debe_quitar_inscripcion_incompatible_antes_de_cambiar_categoria(self):
        nueva_categoria = Categoria.objects.create(nombre="Segunda")
        self.client.force_authenticate(self.admin)
        respuesta = self.client.patch(
            f"/api/admin/jugadores/{self.jugador.pk}/",
            {"nombre": "Ana Editada", "categoria": nueva_categoria.pk},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(self.division.nombre, str(respuesta.data))

        quitar = self.client.patch(
            f"/api/admin/inscripciones/{self.inscripcion.pk}/", {"activa": False}
        )
        self.assertEqual(quitar.status_code, 200, quitar.data)
        respuesta = self.client.patch(
            f"/api/admin/jugadores/{self.jugador.pk}/",
            {"nombre": "Ana Editada", "categoria": nueva_categoria.pk},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.jugador.refresh_from_db()
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.jugador.nombre, "Ana Editada")
        self.assertEqual(self.jugador.categoria, nueva_categoria)
        self.assertEqual(self.inscripcion.categoria, self.categoria)
        self.assertFalse(self.inscripcion.activa)

        volver_categoria = self.client.patch(
            f"/api/admin/jugadores/{self.jugador.pk}/", {"categoria": self.categoria.pk}
        )
        self.assertEqual(volver_categoria.status_code, 200, volver_categoria.data)
        reinscribir = self.client.post(
            f"/api/admin/divisiones/{self.division.pk}/inscripciones/",
            {"jugador": self.jugador.pk},
        )
        self.assertEqual(reinscribir.status_code, 201, reinscribir.data)
        self.assertNotEqual(reinscribir.data["id"], self.inscripcion.pk)
        self.assertEqual(
            InscripcionDivision.objects.filter(
                division=self.division, jugador=self.jugador, activa=True
            ).count(), 1
        )

    def test_panel_admin_puede_consultar_catalogos_y_sesion(self):
        self.client.force_authenticate(self.admin)
        for url in ("/api/auth/me/", "/api/admin/ligas/", "/api/admin/categorias/",
                    "/api/admin/divisiones/", "/api/admin/jugadores/", "/api/admin/partidos/",
                    "/api/admin/torneos/", "/api/admin/puntos-torneo/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_login_y_escritura_exigen_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        sin_token = cliente.post("/api/auth/login/", {"username": "admin", "password": "secreto"})
        self.assertEqual(sin_token.status_code, 403)
        token = cliente.get("/api/auth/csrf/").json()["csrfToken"]
        login = cliente.post("/api/auth/login/", {"username": "admin", "password": "secreto"},
                             content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(login.status_code, 200)
        sin_csrf = cliente.post(f"/api/admin/ligas/{self.liga.pk}/principal/")
        self.assertEqual(sin_csrf.status_code, 403)
        token_rotado = cliente.get("/api/auth/csrf/").json()["csrfToken"]
        con_csrf = cliente.post(f"/api/admin/ligas/{self.liga.pk}/principal/", HTTP_X_CSRFTOKEN=token_rotado)
        self.assertEqual(con_csrf.status_code, 200)

    def test_usuario_no_staff_no_puede_iniciar_sesion(self):
        cliente = Client(enforce_csrf_checks=True)
        token = cliente.get("/api/auth/csrf/").json()["csrfToken"]
        respuesta = cliente.post("/api/auth/login/", {"username": "normal", "password": "secreto"},
                                 content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(respuesta.status_code, 400)

    def test_resultado_invalido_retorna_400_y_no_500(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post("/api/admin/partidos/", {"division": self.division.pk,
            "fecha": str(date.today()), "jugador_a": self.inscripcion.pk, "jugador_b": self.inscripcion.pk,
            "set_1": "6/5", "set_2": "6/0"})
        self.assertEqual(respuesta.status_code, 400)

    def test_administrador_puede_editar_y_anular_partido(self):
        rival = Jugador.objects.create(nombre="Rival API", categoria=self.categoria)
        rival_inscripcion = InscripcionDivision.objects.create(
            division=self.division, jugador=rival, categoria=self.categoria
        )
        self.client.force_authenticate(self.admin)
        creado = self.client.post("/api/admin/partidos/", {
            "division": self.division.pk, "fecha": str(date.today()),
            "jugador_a": self.inscripcion.pk, "jugador_b": rival_inscripcion.pk,
            "set_1": "6/0", "set_2": "6/0",
        })
        self.assertEqual(creado.status_code, 201, creado.data)
        editado = self.client.patch(
            f"/api/admin/partidos/{creado.data['id']}/", {"set_1": "6/1"}
        )
        self.assertEqual(editado.status_code, 200, editado.data)
        self.assertEqual(editado.data["set_1"], "6/1")

        eliminado = self.client.patch(
            f"/api/admin/partidos/{creado.data['id']}/", {"estado": Partido.Estado.ANULADO}
        )
        self.assertEqual(eliminado.status_code, 200, eliminado.data)
        ranking = self.client.get(f"/api/divisiones/{self.division.pk}/ranking/").data
        self.assertTrue(all(fila["puntos_partidos"] == 0 for fila in ranking))
