from django.urls import path, include
from .objects.view_objects.ai_backend_manager import *

urlpatterns = [
    path("status/", StatusManager.as_view()),
    path("task_generation_model/", include("AI_Backend_Endpoint.TaskGenTrainer_Endpoint.urls")),
]
