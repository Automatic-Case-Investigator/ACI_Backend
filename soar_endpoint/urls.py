from django.urls import path
from .objects.view_objects.SOAR_info_view import SOARInfoView
from .objects.view_objects.SOAR_control_view import *

urlpatterns = [
    path("soar_info/", SOARInfoView.as_view()),
    path("organizations/", OrgControlView.as_view()),
    path("case/", CaseControlView.as_view()),
    path("task/", TaskControlView.as_view()),
    path("task_log/", TaskLogControlView.as_view())
]