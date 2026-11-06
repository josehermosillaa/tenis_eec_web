# Despliegue de demostración en Render

El proyecto se publica como un único servicio web: Django sirve la API, el panel y la compilación de Angular. PostgreSQL se crea como un servicio separado dentro del mismo Blueprint.

## Antes de desplegar

1. Subir la rama de demostración al repositorio remoto.
2. Crear una cuenta en Render y vincular el repositorio.
3. En Render, elegir **New > Blueprint**.
4. Seleccionar el repositorio y la rama que se desea mostrar.
5. Confirmar que Render detecte `render.yaml`.

Render solicitará estas variables privadas durante la creación:

- `DJANGO_SUPERUSER_USERNAME`: nombre de acceso del administrador.
- `DJANGO_SUPERUSER_PASSWORD`: contraseña del administrador.
- `DJANGO_SUPERUSER_EMAIL`: correo opcional.

`SECRET_KEY` se genera automáticamente y `DATABASE_URL` se conecta automáticamente con PostgreSQL.

## Después del despliegue

- Aplicación: `https://<nombre-del-servicio>.onrender.com/`
- Panel Angular: `https://<nombre-del-servicio>.onrender.com/admin/`
- Django Admin: `https://<nombre-del-servicio>.onrender.com/django-admin/`
- Estado del servicio: `https://<nombre-del-servicio>.onrender.com/health/`

Las migraciones y la creación o actualización del administrador se ejecutan automáticamente al iniciar el contenedor.

## Datos

La base PostgreSQL nueva comienza sin ligas, jugadores ni partidos. Los datos del archivo SQLite local no se suben al repositorio. Si se necesitan los datos actuales para la demostración, deben exportarse e importarse de forma controlada después de crear PostgreSQL.

La base PostgreSQL gratuita de Render expira a los 30 días. Es apropiada para esta demostración, no para producción permanente.

## Transferir los datos locales a PostgreSQL

Este procedimiento se realiza una vez que la base PostgreSQL y el servicio web ya fueron creados en Render.

Desde PowerShell, dentro de `backend`:

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe manage.py dumpdata tenis --exclude tenis.auditoria --indent 2 --output demo_data.json
Remove-Item Env:PYTHONUTF8
```

En Render, abrir PostgreSQL y copiar desde **Connect** su **External Database URL**. No utilizar la URL interna desde el computador local.

```powershell
$renderDbUrl = Read-Host "External Database URL de Render"
$env:DATABASE_URL = $renderDbUrl
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py loaddata demo_data.json
.\.venv\Scripts\python.exe manage.py shell -c "from apps.tenis.models import Liga, Jugador, Partido; print({'ligas': Liga.objects.count(), 'jugadores': Jugador.objects.count(), 'partidos': Partido.objects.count()})"
Remove-Item Env:DATABASE_URL
```

La URL externa contiene la contraseña de PostgreSQL y no debe guardarse en Git, capturas ni documentación. `demo_data.json` también está ignorado por Git.

La auditoría se excluye porque sus registros apuntan a usuarios de la base SQLite local. En Render comenzará una auditoría nueva asociada al administrador creado allí.
