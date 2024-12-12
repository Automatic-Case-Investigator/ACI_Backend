from django.urls import path
from .objects.view_objects.SOAR_info_manager import SOARInfoManager
from .objects.view_objects.SOAR_control_manager import *
from .objects.view_objects.AI_system_control_manager import *

urlpatterns = [
    path("soar_info/", SOARInfoManager.as_view()),
    path("organizations/", OrgControlManager.as_view()),
    path("case/", CaseControlManager.as_view()),
    path("task/", TaskControlManager.as_view()),
    path("task_log/", TaskLogControlManager.as_view()),
    path("task_generator/", TaskGeneratorControlManager.as_view())
]