# Plan de desarrollo

## Reglas recuperadas del sistema legado

`legacy/codigo.gs` valida sets normales contra una lista cerrada, exige Super Tiebreak cuando cada jugador gana un set y lo valida a 10 con diferencia mínima de dos. Solo partidos terminados aportan estadísticas. Una victoria entrega 3 puntos; el perdedor recibe 1 si cae en dos sets y 2 si cae en Super Tiebreak. El Super Tiebreak suma un set, pero no juegos. El orden es: puntos totales, diferencia de sets, diferencia de juegos, juegos ganados y nombre.

El legado separaba 3ra y 4ta en hojas distintas, relacionaba por nombre y almacenaba torneos en columnas fijas. Esos mecanismos no se trasladan a Django.

## Arquitectura vigente: ligas y divisiones

El requisito de múltiples divisiones reemplaza el ranking general único anterior. Una `Liga` representa una competencia o temporada y contiene una o más `Division`. Cada división tiene sus propias categorías permitidas, inscripciones, partidos, puntos de torneo y ranking. Ningún cálculo cruza divisiones ni ligas.

Una liga puede tener divisiones Primera, Segunda y Tercera-Cuarta. En la última, jugadores de ambas categorías compiten y comparten clasificación. La categoría es el nivel deportivo; la división es el ámbito competitivo.

La liga principal debe estar activa y es única. Al cerrar una liga deja de ser principal, se bloquean modificaciones ordinarias y se conserva un `SnapshotRanking` final por división. La operación transaccional de cierre y generación de snapshots se implementará con la API administrativa.

## Modelo de datos validado

- `Liga`: nombre, fechas, descripción, estado `BORRADOR/ACTIVA/CERRADA` y selección como principal.
- `Categoria`: catálogo deportivo configurable.
- `Division`: pertenece a una liga; nombre y orden son únicos dentro de ella.
- `DivisionCategoria`: categorías permitidas; impide reutilizar una categoría en dos divisiones de la misma liga.
- `Jugador`: identidad global, categoría actual y estado.
- `InscripcionDivision`: une jugador y división una sola vez y conserva la categoría histórica.
- `Partido`: pertenece a una división y referencia dos inscripciones de esa misma división.
- `Torneo`: pertenece a una liga.
- `PuntosTorneo`: pertenece explícitamente a torneo, división e inscripción compatibles.
- `SnapshotRanking`: copia JSON de una clasificación, con un único snapshot final por división.
- `Auditoria`: actor, acción, objeto y cambios JSON.

Se usa `PROTECT` para preservar el historial. Las estadísticas y posiciones ordinarias se derivan; solamente la clasificación final de una liga cerrada se materializa como snapshot.

## Restricciones e invariantes

- Una división requiere al menos una categoría permitida antes de habilitar inscripciones.
- Pareja `(división, jugador)` única.
- Una categoría no puede aparecer en dos divisiones de la misma liga.
- La categoría histórica debe estar permitida y coincidir con la categoría actual al inscribir.
- Los participantes y el partido pertenecen a la misma división.
- Torneo y división pertenecen a la misma liga; la inscripción pertenece a esa división.
- Liga principal única y necesariamente activa.
- Liga cerrada bloquea nuevos partidos y puntos.
- Cambios estructurales que invaliden inscripciones o resultados se rechazarán en servicios administrativos.

Las reglas entre tablas se validan en servicios/modelos porque SQLite no permite expresar todas mediante `CHECK`; las unicidades simples también están protegidas por la base de datos.

## API planificada

- `GET /api/ligas/principal/`
- `GET /api/ligas/{id}/divisiones/`
- `GET /api/divisiones/{id}/ranking/`
- `GET /api/divisiones/{id}/partidos/`
- `GET /api/divisiones/{id}/jugadores/`

La API administrativa protegida incluirá CRUD de ligas/divisiones, categorías permitidas, inscripciones, partidos, torneos, puntos, selección de liga principal y cierre transaccional.

## Frontend planificado (no iniciado)

Angular 20 obtendrá desde la API la liga principal y las divisiones ordenadas. Mostrará pestañas dinámicas; cambiar de pestaña actualizará ranking, resultados y jugadores sin recargar la aplicación. No se implementará hasta validar el dominio y la API.

## Etapas

1. **Dominio y persistencia (completada):** ligas, divisiones, inscripciones, migración, validadores, ranking aislado y pruebas.
2. **Servicios transaccionales (completada):** configuración de categorías, inscripciones, liga principal, cierre atómico con snapshots y auditoría.
3. **API y seguridad (completada):** endpoints públicos/administrativos, sesión, CSRF, permisos y pruebas HTTP.
4. **Frontend Angular 20 (completada para el MVP):** sitio público, pestañas dinámicas, login y panel administrativo responsive para ligas, divisiones, categorías, jugadores, resultados y torneos.
5. **Entrega:** pruebas integrales, Gunicorn/Nginx, respaldo SQLite y operación.

## Decisiones pendientes

- Si un jugador puede inscribirse en más de una división de la misma liga. No se prohibió porque el requisito solo limita una inscripción por división.
- Si los puntos de torneo pueden ser negativos. Se mantienen no negativos por ser puntos adicionales.
- Política excepcional para corregir una liga cerrada.
- Tratamiento visual de una inscripción inactiva antes del cierre.

## Servicios transaccionales implementados

- `configurar_categorias_division`: exige al menos una categoría, evita repeticiones dentro de la liga y no permite retirar categorías ya utilizadas.
- `inscribir_jugador`: valida liga, estado, categoría permitida, duplicidad y guarda la categoría histórica.
- `establecer_liga_principal`: bloquea las ligas implicadas y cambia la principal únicamente hacia una liga activa.
- `cerrar_liga`: valida todas las divisiones, genera un snapshot final serializable por división y cierra la liga en una sola transacción. Ante cualquier error no persiste ningún snapshot ni cambio de estado.

Todos registran una entrada de `Auditoria` dentro de la misma transacción. La futura API debe invocar estos servicios y no duplicar sus reglas en serializers o vistas.

## API implementada

La API pública expone liga principal, divisiones dinámicas, ranking, partidos y jugadores por división, además de consultas generales de jugadores, partidos y torneos. Para una liga cerrada, el ranking devuelve el snapshot final y no recalcula datos históricos mutables.

La API administrativa permite crear y editar jugadores, ligas, divisiones, partidos, torneos y puntos; configurar categorías; inscribir jugadores; seleccionar la liga principal y cerrar una liga. Las escrituras exigen usuario `is_staff`, sesión válida y CSRF. El login también está protegido por CSRF y rechaza cuentas no administrativas. Las creaciones y ediciones genéricas generan auditoría en la misma transacción.

Angular deberá obtener primero el token en `GET /api/auth/csrf/`, enviarlo en `X-CSRFToken`, conservar la cookie de sesión y volver a obtener el token después del login porque Django lo rota.
