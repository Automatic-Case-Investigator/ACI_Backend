from django.urls import path
from . import views

urlpatterns = [
    path("get_jobs/", views.get_jobs, name="get_jobs"),
    path("remove_job/", views.remove_job, name="remove_job"),
]