FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBUG=False

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist/tenis-eec/browser/ ./frontend/dist/tenis-eec/browser/

WORKDIR /app/backend
RUN SECRET_KEY=build-only-secret python manage.py collectstatic --noinput

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_demo && python manage.py ensure_admin && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
