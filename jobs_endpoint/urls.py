from django.urls import path
from .objects.view_objects.job_control_view import *

urlpatterns = [
    path("", JobControlView.as_view())
]