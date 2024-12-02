from django.urls import path
from .objects.view_objects.SOARInfoManager import SOARInfoManager
from .objects.view_objects.SOARControlManager import *
from .objects.view_objects.AISystemContolManager import *

urlpatterns = [
    path("soar_info/", SOARInfoManager.as_view()),
    path("organizations/", OrgControlManager.as_view()),
    path("case/", CaseControlManager.as_view()),
    path("task/", TaskControlManager.as_view()),
    path("task_log/", TaskLogControlManager.as_view()),
    path("task_generator/", TaskGeneratorControlManager.as_view())
]