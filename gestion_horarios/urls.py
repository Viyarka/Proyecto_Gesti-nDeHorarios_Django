from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("horarios.urls")),
    path("favicon.ico", RedirectView.as_view(url="/static/horarios/favicon.ico", permanent=False)),
]
