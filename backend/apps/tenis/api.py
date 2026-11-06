from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Auditoria, Categoria, Division, InscripcionDivision, Jugador, Liga, Partido, PuntosTorneo, Torneo
from .serializers import (CategoriaSerializer, ConfigurarCategoriasSerializer, DivisionSerializer, EditarDivisionSerializer, InscripcionSerializer,
    InscripcionEstadoSerializer, InscribirSerializer, JugadorSerializer, LigaSerializer, LoginSerializer, PartidoSerializer,
    PuntosTorneoSerializer, TorneoSerializer)
from .services import (calcular_ranking, cambiar_estado_division, cerrar_liga, configurar_categorias_division, editar_division,
                       eliminar_division, establecer_liga_principal, inscribir_jugador)

class CsrfView(APIView):
    permission_classes = [AllowAny]
    def get(self, request): return Response({"csrfToken": get_token(request)})

@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        serializer = LoginSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if not user or not user.is_active or not user.is_staff:
            return Response({"detail": "Credenciales administrativas inválidas."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response({"id": user.pk, "username": user.get_username()})

class LogoutView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request): logout(request); return Response(status=status.HTTP_204_NO_CONTENT)

class SesionView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request): return Response({"id": request.user.pk, "username": request.user.get_username()})

class LigaPrincipalView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        liga = get_object_or_404(Liga, es_principal=True, estado=Liga.Estado.ACTIVA)
        return Response(LigaSerializer(liga).data)

class DivisionesLigaView(generics.ListAPIView):
    permission_classes = [AllowAny]; serializer_class = DivisionSerializer
    def get_queryset(self): return Division.objects.filter(liga_id=self.kwargs["pk"], estado=Division.Estado.ACTIVA).prefetch_related("categorias")

class RankingDivisionView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        division = get_object_or_404(Division, pk=pk)
        if division.liga.estado == Liga.Estado.CERRADA:
            snapshot = division.snapshots_ranking.filter(es_final=True).first()
            if snapshot: return Response(snapshot.datos)
        datos = []
        for f in calcular_ranking(division):
            datos.append({"posicion": f["posicion"], "inscripcion_id": f["inscripcion"].pk,
                "jugador_id": f["jugador"].pk, "jugador": f["jugador"].nombre,
                "categoria": f["categoria"].nombre, **{k: f[k] for k in ("puntos_partidos", "puntos_torneos",
                "puntos_totales", "partidos", "ganados", "perdidos", "sets_ganados", "sets_perdidos",
                "diferencia_sets", "juegos_ganados", "juegos_perdidos", "diferencia_juegos")}})
        return Response(datos)

class PartidosDivisionView(generics.ListAPIView):
    permission_classes = [AllowAny]; serializer_class = PartidoSerializer
    def get_queryset(self):
        return Partido.objects.filter(division_id=self.kwargs["pk"], estado=Partido.Estado.TERMINADO).select_related("jugador_a__jugador", "jugador_b__jugador", "ganador__jugador")

class JugadoresDivisionView(generics.ListAPIView):
    permission_classes = [AllowAny]; serializer_class = InscripcionSerializer
    def get_queryset(self): return InscripcionDivision.objects.filter(division_id=self.kwargs["pk"]).select_related("jugador__categoria", "categoria")

class JugadoresView(generics.ListAPIView):
    permission_classes = [AllowAny]; serializer_class = JugadorSerializer
    queryset = Jugador.objects.select_related("categoria").all()

class JugadorDetalleView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]; serializer_class = JugadorSerializer
    queryset = Jugador.objects.select_related("categoria").all()

class PerfilJugadorView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        jugador = get_object_or_404(Jugador.objects.select_related("categoria"), pk=pk)
        inscripcion = jugador.inscripciones.filter(
            activa=True, division__estado=Division.Estado.ACTIVA, division__liga__es_principal=True, division__liga__estado=Liga.Estado.ACTIVA
        ).select_related("division__liga", "categoria").first()
        respuesta = {"jugador": JugadorSerializer(jugador).data, "liga": None, "division": None,
                     "estadisticas": None, "partidos": [], "ranking": []}
        if not inscripcion:
            return Response(respuesta)
        division = inscripcion.division
        ranking = calcular_ranking(division)
        fila = next((f for f in ranking if f["inscripcion"].pk == inscripcion.pk), None)
        campos = ("posicion", "puntos_partidos", "puntos_torneos", "puntos_totales", "partidos",
                  "ganados", "perdidos", "diferencia_sets", "diferencia_juegos")
        respuesta["liga"] = LigaSerializer(division.liga).data
        respuesta["division"] = DivisionSerializer(division).data
        respuesta["estadisticas"] = {campo: fila[campo] for campo in campos} if fila else {
            campo: 0 for campo in campos
        }
        respuesta["ranking"] = [{
            "posicion": f["posicion"], "jugador_id": f["jugador"].pk, "jugador": f["jugador"].nombre,
            "partidos": f["partidos"], "ganados": f["ganados"], "perdidos": f["perdidos"],
            "categoria": f["categoria"].nombre, "diferencia_sets": f["diferencia_sets"],
            "puntos_totales": f["puntos_totales"],
        } for f in ranking]
        partidos = Partido.objects.filter(
            Q(jugador_a=inscripcion) | Q(jugador_b=inscripcion), estado=Partido.Estado.TERMINADO
        ).select_related("jugador_a__jugador", "jugador_b__jugador", "ganador__jugador")
        respuesta["partidos"] = [{
            "id": p.pk, "fecha": p.fecha, "rival": p.jugador_b.jugador.nombre if p.jugador_a_id == inscripcion.pk else p.jugador_a.jugador.nombre,
            "ganado": p.ganador_id == inscripcion.pk, "set_1": p.set_1, "set_2": p.set_2,
            "super_tiebreak": p.super_tiebreak,
        } for p in partidos]
        return Response(respuesta)

class PartidosJugadorView(generics.ListAPIView):
    permission_classes = [AllowAny]; serializer_class = PartidoSerializer
    def get_queryset(self):
        return Partido.objects.filter(Q(jugador_a__jugador_id=self.kwargs["pk"]) | Q(jugador_b__jugador_id=self.kwargs["pk"]),
                                      estado=Partido.Estado.TERMINADO).select_related("jugador_a__jugador", "jugador_b__jugador", "ganador__jugador")

class PartidosView(generics.ListAPIView):
    permission_classes = [AllowAny]; serializer_class = PartidoSerializer
    queryset = Partido.objects.filter(estado=Partido.Estado.TERMINADO).select_related("jugador_a__jugador", "jugador_b__jugador", "ganador__jugador")

class TorneosView(generics.ListAPIView):
    permission_classes = [AllowAny]; serializer_class = TorneoSerializer
    queryset = Torneo.objects.filter(anulado=False)

class AdminCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    def perform_create(self, serializer):
        with transaction.atomic():
            objeto = serializer.save()
            cambios = {campo: str(valor) for campo, valor in serializer.validated_data.items()}
            Auditoria.objects.create(usuario=self.request.user, accion="CREAR", modelo=objeto._meta.label,
                                      objeto_id=str(objeto.pk), cambios=cambios)

class AdminLigaCreateView(AdminCreateView): serializer_class = LigaSerializer; queryset = Liga.objects.all()
class AdminCategoriaCreateView(AdminCreateView): serializer_class = CategoriaSerializer; queryset = Categoria.objects.all()
class AdminJugadorCreateView(AdminCreateView): serializer_class = JugadorSerializer; queryset = Jugador.objects.all()
class AdminDivisionCreateView(AdminCreateView): serializer_class = DivisionSerializer; queryset = Division.objects.all()
class AdminPartidoCreateView(AdminCreateView): serializer_class = PartidoSerializer; queryset = Partido.objects.all()
class AdminTorneoCreateView(AdminCreateView): serializer_class = TorneoSerializer; queryset = Torneo.objects.all()
class AdminPuntosCreateView(AdminCreateView): serializer_class = PuntosTorneoSerializer; queryset = PuntosTorneo.objects.all()

class AdminUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAdminUser]
    def perform_update(self, serializer):
        with transaction.atomic():
            objeto = serializer.save()
            cambios = {campo: str(valor) for campo, valor in serializer.validated_data.items()}
            Auditoria.objects.create(usuario=self.request.user, accion="EDITAR", modelo=objeto._meta.label,
                                      objeto_id=str(objeto.pk), cambios=cambios)

class AdminLigaUpdateView(AdminUpdateView): serializer_class = LigaSerializer; queryset = Liga.objects.all()
class AdminCategoriaUpdateView(AdminUpdateView): serializer_class = CategoriaSerializer; queryset = Categoria.objects.all()
class AdminJugadorUpdateView(AdminUpdateView): serializer_class = JugadorSerializer; queryset = Jugador.objects.all()
class AdminInscripcionUpdateView(AdminUpdateView):
    serializer_class = InscripcionEstadoSerializer
    queryset = InscripcionDivision.objects.select_related("division__liga", "jugador").all()
class AdminDivisionUpdateView(AdminUpdateView):
    serializer_class = DivisionSerializer; queryset = Division.objects.all()
    def patch(self, request, *args, **kwargs):
        serializer = EditarDivisionSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        division = editar_division(self.get_object(), usuario=request.user, **serializer.validated_data)
        return Response(DivisionSerializer(division).data)
    def delete(self, request, *args, **kwargs):
        eliminar_division(self.get_object(), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
class AdminPartidoUpdateView(AdminUpdateView): serializer_class = PartidoSerializer; queryset = Partido.objects.all()
class AdminTorneoUpdateView(AdminUpdateView): serializer_class = TorneoSerializer; queryset = Torneo.objects.all()
class AdminPuntosUpdateView(AdminUpdateView): serializer_class = PuntosTorneoSerializer; queryset = PuntosTorneo.objects.all()

class AdminConfigurarCategoriasView(APIView):
    permission_classes = [IsAdminUser]
    def put(self, request, pk):
        serializer = ConfigurarCategoriasSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        division = get_object_or_404(Division, pk=pk)
        configurar_categorias_division(division, serializer.validated_data["categorias"], request.user)
        return Response(DivisionSerializer(division).data)

class AdminEstadoDivisionView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, pk, estado):
        division = cambiar_estado_division(get_object_or_404(Division, pk=pk), estado, request.user)
        return Response(DivisionSerializer(division).data)

class AdminInscribirView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, pk):
        serializer = InscribirSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        inscripcion = inscribir_jugador(get_object_or_404(Division, pk=pk), serializer.validated_data["jugador"], request.user)
        return Response(InscripcionSerializer(inscripcion).data, status=status.HTTP_201_CREATED)

class AdminPrincipalView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, pk):
        liga = establecer_liga_principal(get_object_or_404(Liga, pk=pk), request.user)
        return Response(LigaSerializer(liga).data)

class AdminCerrarLigaView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, pk):
        snapshots = cerrar_liga(get_object_or_404(Liga, pk=pk), request.user)
        return Response({"liga_id": pk, "snapshots": [s.pk for s in snapshots]})
