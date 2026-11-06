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
from .serializers import (CategoriaSerializer, ConfigurarCategoriasSerializer, DivisionSerializer, InscripcionSerializer,
    InscribirSerializer, JugadorSerializer, LigaSerializer, LoginSerializer, PartidoSerializer,
    PuntosTorneoSerializer, TorneoSerializer)
from .services import (calcular_ranking, cerrar_liga, configurar_categorias_division,
                       establecer_liga_principal, inscribir_jugador)

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
    def get_queryset(self): return Division.objects.filter(liga_id=self.kwargs["pk"]).prefetch_related("categorias")

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
class AdminDivisionUpdateView(AdminUpdateView): serializer_class = DivisionSerializer; queryset = Division.objects.all()
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
