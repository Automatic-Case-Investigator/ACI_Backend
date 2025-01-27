from .objects.view_objects.ai_backend_view import *
from django.urls import path, include

urlpatterns = [
    path("status/", StatusView.as_view()),
    path("task_generation_model/", include("ai_system_endpoint.task_generation.urls")),
    path("automatic_investigation/", include("ai_system_endpoint.automatic_investigation.urls")),
]
