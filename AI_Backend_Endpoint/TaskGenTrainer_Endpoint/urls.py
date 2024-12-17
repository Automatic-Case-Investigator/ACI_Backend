from django.urls import path
from .objects.view_objects.task_gen_trainer_manager import *

urlpatterns = [
    path("case_tmp_storage/", CaseTemporaryStorageManager.as_view()),
    path("train_model/", TaskGenTrainerManager.as_view()),
    path("restore_baseline/", RestoreManager.as_view()),
]