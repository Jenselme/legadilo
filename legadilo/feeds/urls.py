from django.urls import path

from . import views

app_name = "feeds"

urlpatterns = [
    path("", views.create_feed, name="create_feed"),
]
