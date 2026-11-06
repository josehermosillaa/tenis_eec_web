from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("apps.tenis.urls")),
    path("health/", lambda request: JsonResponse({"status": "ok"})),
    re_path(r"^(?!api/|django-admin/|health/).*$", TemplateView.as_view(template_name="index.html")),
]
