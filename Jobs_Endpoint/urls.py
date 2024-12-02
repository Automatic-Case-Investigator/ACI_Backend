from django.urls import path
from .objects.view_objects.jobControlManager import *

urlpatterns = [
    path("", JobControlManager.as_view())
]