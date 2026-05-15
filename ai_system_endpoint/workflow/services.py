from ai_system_endpoint.workflow.objects.workflow.workflow_execution_service import (
    WorkflowExecutionService,
)
from ai_system_endpoint.workflow.objects.workflow.workflow_run_service import WorkflowRunService
from ai_system_endpoint.workflow.objects.workflow.workflow_settings_service import (
    WorkflowSettingsService,
)

workflow_settings_service = WorkflowSettingsService()
workflow_run_service = WorkflowRunService(workflow_settings_service)
workflow_execution_service = WorkflowExecutionService(workflow_settings_service, workflow_run_service)
