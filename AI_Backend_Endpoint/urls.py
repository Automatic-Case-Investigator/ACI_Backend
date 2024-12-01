from django.urls import path, include

urlpatterns = [
    path("task_generation_model/", include("AI_Backend_Endpoint.TaskGenTrainer_Endpoint.urls")),
]
