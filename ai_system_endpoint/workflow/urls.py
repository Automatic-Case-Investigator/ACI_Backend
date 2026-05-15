from django.urls import path

from ai_system_endpoint.workflow.objects.view_objects.workflow_settings_view import *
from ai_system_endpoint.workflow.objects.view_objects.workflow_webhook_ingest_view import *

urlpatterns = [
    path("webhook/case-ingest/", WorkflowWebhookIngestView.as_view()),
    path("settings/", WorkflowSettingsView.as_view()),
]
