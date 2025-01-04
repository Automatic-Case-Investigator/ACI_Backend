from .objects.view_objects.ai_backend_view import *
from django.urls import path, include

urlpatterns = [
    path("status/", StatusView.as_view()),
    path("task_generation_model/", include("AI_Backend_Endpoint.TaskGenTrainer_Endpoint.urls")),
]
