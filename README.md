# Ranking General de Tenis

Primera etapa del sistema web que migra la lógica de `legacy/codigo.gs` a Django. Incluye ligas con múltiples divisiones, inscripciones con categoría histórica y ranking independiente por división. Angular se inicia en una etapa posterior.

## Requisitos

- Python 3.11 o superior
- Django 5.2 LTS
- SQLite3 (incluido con Python)

## Instalación y ejecución

En PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

El administrador Django queda en `http://127.0.0.1:8000/django-admin/` y la API bajo `http://127.0.0.1:8000/api/`.

En otra terminal, inicia Angular:

```powershell
cd frontend
npm install
npm start
```

La interfaz queda en `http://localhost:4200/`; el servidor de desarrollo redirige `/api` a Django mediante `proxy.conf.json`.

## Pruebas

```powershell
cd backend
python manage.py test
```

Las pruebas cubren reglas deportivas, aislamiento de rankings, operaciones transaccionales, snapshots, auditoría, endpoints públicos, permisos administrativos, login de sesión, rotación CSRF y respuestas de validación.

## Arquitectura

El dominio vive en `apps.tenis`. Los validadores y el ranking están en `services.py`; cada cálculo recibe una división explícita y nunca mezcla datos de otras divisiones o ligas.

Consulta [PLAN.md](PLAN.md) para el análisis del legado, diferencias y siguientes etapas.
