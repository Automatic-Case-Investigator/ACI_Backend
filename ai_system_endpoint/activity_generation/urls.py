from ai_system_endpoint.activity_generation.objects.view_objects.activity_generation_view import (
    ActivityGenerationView,
)
from django.urls import path

urlpatterns = [
    path("generate/", ActivityGenerationView.as_view()),
]
