from .objects.view_objects.ai_backend_view import *
from django.urls import path, include
from ai_system_endpoint.settings.objects.view_objects.automation_settings_view import (
    AutomationSettingsView,
)

urlpatterns = [
    path("status/", StatusView.as_view()),
    path("task_generation_model/", include("ai_system_endpoint.task_generation.urls")),
    path(
        "activity_generation_model/",
        include("ai_system_endpoint.activity_generation.urls"),
    ),
    path(
        "automatic_investigation/",
        include("ai_system_endpoint.automatic_investigation.urls"),
    ),
    path("report_generation/", include("ai_system_endpoint.report_generation.urls")),
    path("settings/", include("ai_system_endpoint.settings.urls")),
    path("automation_settings/", AutomationSettingsView.as_view()),
    path("workflow/", include("ai_system_endpoint.workflow.urls")),
]
