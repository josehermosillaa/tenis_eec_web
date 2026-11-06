from datetime import date
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APITestCase
from apps.tenis.models import Categoria, Division, DivisionCategoria, InscripcionDivision, Jugador, Liga

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
