from django.urls import path

from . import views

app_name = "feeds"

urlpatterns = [
    path("", views.subscribe_to_feed, name="subscribe_to_feed"),
]
