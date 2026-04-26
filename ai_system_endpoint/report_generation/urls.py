from .objects.view_objects.report_generation_view import *
from django.urls import path

urlpatterns = [
    path("generate/", ReportGenerationView.as_view()),
]
