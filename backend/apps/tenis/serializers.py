from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import (Categoria, Division, DivisionCategoria, InscripcionDivision, Jugador,
                     Liga, Partido, PuntosTorneo, Torneo)

class ModeloValidadoSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        try: return super().create(validated_data)
        except DjangoValidationError as exc: raise serializers.ValidationError(getattr(exc, "message_dict", exc.messages))
    def update(self, instance, validated_data):
        try: return super().update(instance, validated_data)
        except DjangoValidationError as exc: raise serializers.ValidationError(getattr(exc, "message_dict", exc.messages))

class CategoriaSerializer(ModeloValidadoSerializer):
    class Meta: model = Categoria; fields = ("id", "nombre")

class LigaSerializer(ModeloValidadoSerializer):
    class Meta: model = Liga; fields = ("id", "nombre", "fecha_inicio", "fecha_fin", "estado", "es_principal", "descripcion")
    read_only_fields = ("es_principal", "fecha_fin")
    def validate_estado(self, value):
        if value == Liga.Estado.CERRADA: raise serializers.ValidationError("Use la operación específica para cerrar la liga.")
        return value

class DivisionSerializer(ModeloValidadoSerializer):
    categorias = CategoriaSerializer(many=True, read_only=True)
    class Meta: model = Division; fields = ("id", "liga", "nombre", "orden", "categorias")

class JugadorSerializer(ModeloValidadoSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    class Meta: model = Jugador; fields = ("id", "nombre", "categoria", "categoria_nombre", "estado")

class InscripcionSerializer(ModeloValidadoSerializer):
    jugador_detalle = JugadorSerializer(source="jugador", read_only=True)
    categoria_historica = serializers.CharField(source="categoria.nombre", read_only=True)
    class Meta:
        model = InscripcionDivision
        fields = ("id", "division", "jugador", "jugador_detalle", "categoria", "categoria_historica", "activa", "inscrito_en")
        read_only_fields = ("categoria", "categoria_historica", "inscrito_en")

class PartidoSerializer(ModeloValidadoSerializer):
    jugador_a_nombre = serializers.CharField(source="jugador_a.jugador.nombre", read_only=True)
    jugador_b_nombre = serializers.CharField(source="jugador_b.jugador.nombre", read_only=True)
    ganador_nombre = serializers.CharField(source="ganador.jugador.nombre", read_only=True)
    class Meta:
        model = Partido
        fields = ("id", "division", "fecha", "jugador_a", "jugador_a_nombre", "jugador_b", "jugador_b_nombre",
                  "set_1", "set_2", "super_tiebreak", "ganador", "ganador_nombre", "estado")
        read_only_fields = ("ganador",)

class TorneoSerializer(ModeloValidadoSerializer):
    class Meta: model = Torneo; fields = ("id", "liga", "nombre", "fecha", "descripcion", "anulado")

class PuntosTorneoSerializer(ModeloValidadoSerializer):
    class Meta: model = PuntosTorneo; fields = ("id", "torneo", "division", "inscripcion", "puntos", "anulado")

class ConfigurarCategoriasSerializer(serializers.Serializer):
    categorias = serializers.PrimaryKeyRelatedField(queryset=Categoria.objects.filter(activa=True), many=True, allow_empty=False)

class InscribirSerializer(serializers.Serializer):
    jugador = serializers.PrimaryKeyRelatedField(queryset=Jugador.objects.all())

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)
