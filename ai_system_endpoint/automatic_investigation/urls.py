import ai_system_endpoint.automatic_investigation.objects.view_objects.activity_generation_view as ActivityGenerationView
import ai_system_endpoint.automatic_investigation.objects.view_objects.query_generation_view as QueryGenerationView
from .objects.view_objects.automatic_investigation_view import *
from django.urls import path

urlpatterns = [
    # TODO: Paths for investigation main control flow activation (investigation should start here)
    path("investigate/", AutomaticInvestigationView.as_view()),

    # TODO: Paths for activity generation (for misc usage)
    
    # path("activity_generation_model/generate/", TaskGenerationView.as_view()),
    # path("activity_generation_model/history/", HistoryView.as_view()),
    # path("activity_generation_model/backup/", BackupView.as_view()),
    # path("activity_generation_model/rollback/", RollbackView.as_view()),
    # path("activity_generation_model/current_backup_version/", CurrentBackupVersionView.as_view()),
    # path("activity_generation_model/case_tmp_storage/", CaseTemporaryStorageView.as_view()),
    # path("activity_generation_model/train_model/", TaskGenTrainerView.as_view()),
    path("activity_generation_model/restore_baseline/", ActivityGenerationView.RestoreView.as_view()),
    
    # TODO: Paths for SIEM investigation
    path("query_generation_model/restore_baseline/", QueryGenerationView.RestoreView.as_view()),
]