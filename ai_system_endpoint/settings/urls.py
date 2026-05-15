from django.urls import path

from ai_system_endpoint.settings.objects.view_objects.settings_view import (
    SettingsView,
)

urlpatterns = [
    path("", SettingsView.as_view()),
]
