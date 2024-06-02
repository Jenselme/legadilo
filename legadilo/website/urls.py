from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "website"

urlpatterns = [
    path("about/", TemplateView.as_view(template_name="website/about.html"), name="about"),
    path("manifest.json", views.manifest_view, name="manifest"),
    path("favicon.ico", views.default_favicon_view, name="favicon"),
]
