# Initial schema compatible with Django 5.2 LTS.

import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=30, unique=True)),
                ('activa', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Division',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('orden', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['orden', 'nombre', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Auditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accion', models.CharField(max_length=30)),
                ('modelo', models.CharField(max_length=80)),
                ('objeto_id', models.CharField(max_length=80)),
                ('cambios', models.JSONField(default=dict)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-creado_en', '-id'],
            },
        ),
        migrations.CreateModel(
            name='DivisionCategoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='configuraciones_division', to='tenis.categoria')),
                ('division', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='categorias_permitidas', to='tenis.division')),
            ],
        ),
        migrations.AddField(
            model_name='division',
            name='categorias',
            field=models.ManyToManyField(related_name='divisiones', through='tenis.DivisionCategoria', to='tenis.categoria'),
        ),
        migrations.CreateModel(
            name='Jugador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150)),
                ('estado', models.CharField(choices=[('ACTIVO', 'Activo'), ('RETIRADO', 'Retirado')], db_index=True, default='ACTIVO', max_length=10)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='jugadores', to='tenis.categoria')),
            ],
            options={
                'ordering': ['nombre', 'id'],
            },
        ),
        migrations.CreateModel(
            name='InscripcionDivision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activa', models.BooleanField(db_index=True, default=True)),
                ('inscrito_en', models.DateTimeField(auto_now_add=True)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inscripciones_historicas', to='tenis.categoria')),
                ('division', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inscripciones', to='tenis.division')),
                ('jugador', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inscripciones', to='tenis.jugador')),
            ],
        ),
        migrations.CreateModel(
            name='Liga',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150, unique=True)),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('BORRADOR', 'Borrador'), ('ACTIVA', 'Activa'), ('CERRADA', 'Cerrada')], db_index=True, default='BORRADOR', max_length=10)),
                ('es_principal', models.BooleanField(db_index=True, default=False)),
                ('descripcion', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-fecha_inicio', 'nombre'],
                'constraints': [models.UniqueConstraint(condition=models.Q(('es_principal', True)), fields=('es_principal',), name='una_liga_principal'), models.CheckConstraint(condition=models.Q(('es_principal', False), ('estado', 'ACTIVA'), _connector='OR'), name='liga_principal_activa')],
            },
        ),
        migrations.AddField(
            model_name='division',
            name='liga',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='divisiones', to='tenis.liga'),
        ),
        migrations.CreateModel(
            name='Partido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('set_1', models.CharField(max_length=7)),
                ('set_2', models.CharField(max_length=7)),
                ('super_tiebreak', models.CharField(blank=True, max_length=15)),
                ('estado', models.CharField(choices=[('TERMINADO', 'Terminado'), ('ANULADO', 'Anulado')], db_index=True, default='TERMINADO', max_length=10)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('division', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='partidos', to='tenis.division')),
                ('ganador', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='partidos_ganados', to='tenis.inscripciondivision')),
                ('jugador_a', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='partidos_como_a', to='tenis.inscripciondivision')),
                ('jugador_b', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='partidos_como_b', to='tenis.inscripciondivision')),
            ],
            options={
                'ordering': ['-fecha', '-id'],
            },
        ),
        migrations.CreateModel(
            name='SnapshotRanking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('generado_en', models.DateTimeField(auto_now_add=True)),
                ('datos', models.JSONField()),
                ('es_final', models.BooleanField(default=False)),
                ('division', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='snapshots_ranking', to='tenis.division')),
            ],
            options={
                'ordering': ['-generado_en', '-id'],
            },
        ),
        migrations.CreateModel(
            name='Torneo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150)),
                ('fecha', models.DateField()),
                ('descripcion', models.TextField(blank=True)),
                ('anulado', models.BooleanField(db_index=True, default=False)),
                ('liga', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='torneos', to='tenis.liga')),
            ],
            options={
                'ordering': ['-fecha', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='PuntosTorneo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puntos', models.IntegerField()),
                ('anulado', models.BooleanField(db_index=True, default=False)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('division', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='puntos_torneo', to='tenis.division')),
                ('inscripcion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='puntos_torneo', to='tenis.inscripciondivision')),
                ('torneo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='asignaciones', to='tenis.torneo')),
            ],
        ),
        migrations.AddConstraint(
            model_name='divisioncategoria',
            constraint=models.UniqueConstraint(fields=('division', 'categoria'), name='categoria_unica_en_division'),
        ),
        migrations.AddConstraint(
            model_name='jugador',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('nombre'), name='jugador_nombre_ci_unico'),
        ),
        migrations.AddConstraint(
            model_name='inscripciondivision',
            constraint=models.UniqueConstraint(fields=('division', 'jugador'), name='jugador_unico_por_division'),
        ),
        migrations.AddConstraint(
            model_name='division',
            constraint=models.UniqueConstraint(fields=('liga', 'nombre'), name='division_nombre_unico_por_liga'),
        ),
        migrations.AddConstraint(
            model_name='division',
            constraint=models.UniqueConstraint(fields=('liga', 'orden'), name='division_orden_unico_por_liga'),
        ),
        migrations.AddConstraint(
            model_name='partido',
            constraint=models.CheckConstraint(condition=models.Q(('jugador_a', models.F('jugador_b')), _negated=True), name='inscripciones_partido_distintas'),
        ),
        migrations.AddConstraint(
            model_name='snapshotranking',
            constraint=models.UniqueConstraint(condition=models.Q(('es_final', True)), fields=('division',), name='un_snapshot_final_por_division'),
        ),
        migrations.AddConstraint(
            model_name='torneo',
            constraint=models.UniqueConstraint(fields=('liga', 'nombre'), name='torneo_nombre_unico_por_liga'),
        ),
        migrations.AddConstraint(
            model_name='puntostorneo',
            constraint=models.UniqueConstraint(fields=('torneo', 'division', 'inscripcion'), name='puntos_unicos_torneo_division_inscripcion'),
        ),
        migrations.AddConstraint(
            model_name='puntostorneo',
            constraint=models.CheckConstraint(condition=models.Q(('puntos__gte', 0)), name='puntos_torneo_no_negativos'),
        ),
    ]
