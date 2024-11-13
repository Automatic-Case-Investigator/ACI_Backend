from django.urls import path
from . import views

urlpatterns = [
    path("get_jobs/", views.get_jobs, name="get_jobs"),
]