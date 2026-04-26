from django.urls import path

from ai_system_endpoint.agent_settings.objects.view_objects.agent_settings_view import (
    AgentSettingsView,
)

urlpatterns = [
    path("", AgentSettingsView.as_view()),
]
