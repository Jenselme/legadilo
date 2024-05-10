from django.urls import path
from django.views.generic import TemplateView

app_name = "website"

urlpatterns = [
    path("about/", TemplateView.as_view(template_name="website/about.html"), name="about"),
]
