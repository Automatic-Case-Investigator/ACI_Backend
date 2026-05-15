from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.utils import timezone as django_timezone

from ACI_Backend.objects.redis_client.redis_client import redis_client
from ai_system_endpoint.activity_generation.objects.activity_generation.activity_generator import (
    ActivityGenerator,
)
from ai_system_endpoint.automatic_investigation.objects.investigator.investigator import (
    Investigator,
)
from ai_system_endpoint.models import WorkflowEvent, WorkflowRun, WorkflowRunStep
from ai_system_endpoint.report_generation.objects.report_generator.report_generator import (
    ReportGenerator,
)
from ai_system_endpoint.task_generation.objects.task_generation.task_generator import (
    TaskGenerator,
)
from ai_system_endpoint.workflow.objects.workflow.workflow_run_service import (
    STEP_SEQUENCE,
    WorkflowRunService,
)
from ai_system_endpoint.workflow.objects.workflow.workflow_settings_service import (
    WorkflowSettingsService,
)
from soar_endpoint.objects.soar_wrapper import soar_wrapper
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder


logger = logging.getLogger(__name__)

STEP_RETRYABLE_HINTS = ("timeout", "temporarily", "connection", "429", "502", "503", "504")


class WorkflowExecutionService:
    def __init__(
        self,
        settings_service: WorkflowSettingsService,
        run_service: WorkflowRunService,
    ):
        self.settings_service = settings_service
        self.run_service = run_service

    def enqueue_workflow_run(self, run_id: str) -> None:
        redis_client.rpush(settings.WORKFLOW_QUEUE_KEY, str(run_id))

    def acquire_workflow_slot(
        self, max_concurrent_workflows: int
    ) -> tuple[str | None, str | None]:
        token = str(uuid.uuid4())
        for index in range(max_concurrent_workflows):
            slot_key = f"{settings.WORKFLOW_SLOT_KEY_PREFIX}:{index}"
            if redis_client.set(slot_key, token, nx=True, ex=settings.WORKFLOW_SLOT_TTL_SECONDS):
                return slot_key, token
        return None, None

    def release_workflow_slot(self, slot_key: str | None, token: str | None) -> None:
        if not slot_key or not token:
            return
        current_token = redis_client.get(slot_key)
        if current_token == token:
            redis_client.delete(slot_key)

    def verify_webhook_signature(
        self, timestamp_header: str, signature_header: str, raw_body: bytes
    ) -> bool:
        # Webhook is open for free access
        return True

    def _infer_error_code(self, message: str) -> str:
        lower_message = message.lower()
        if "timeout" in lower_message:
            return "timeout"
        if "not found" in lower_message:
            return "not_found"
        if "invalid" in lower_message:
            return "validation_error"
        if "connection" in lower_message:
            return "connection_error"
        return "internal_error"

    def _is_retryable(self, message: str, error_code: str) -> bool:
        lower_message = message.lower()
        return error_code in {"timeout", "connection_error", "internal_error"} and any(
            hint in lower_message for hint in STEP_RETRYABLE_HINTS
        )

    def _normalize_step_result(self, result: dict | str | None) -> dict:
        if result is None:
            return {"ok": True, "payload": {}}
        if isinstance(result, dict):
            if "error" in result:
                message = str(result.get("error", "Unknown error"))
                error_code = str(result.get("error_code") or self._infer_error_code(message))
                return {
                    "ok": False,
                    "error_code": error_code,
                    "error_message": message,
                    "retryable": self._is_retryable(message, error_code),
                }
            return {"ok": True, "payload": result}
        return {"ok": True, "payload": {"result": result}}

    def _execute_task_generation_step(self, run: WorkflowRun, step: WorkflowRunStep) -> dict:
        soar_wrapper = SOARWrapperBuilder().build_from_model_object(run.soar)
        case_data = soar_wrapper.get_case(case_id=run.case_id)
        if isinstance(case_data, dict) and "error" in case_data:
            return {
                "error": case_data["error"],
                "error_code": self._infer_error_code(case_data["error"]),
            }

        generator = TaskGenerator()
        generator.set_soarwrapper(soar_wrapper)
        return generator.generate_task(
            case_data=case_data,
            web_search_enabled=bool(step.input_payload.get("use_web_search", False)),
            additional_notes=step.input_payload.get("additional_notes"),
        )

    def _execute_activity_generation_step(self, run: WorkflowRun, step: WorkflowRunStep) -> dict:
        soar_wrapper = SOARWrapperBuilder().build_from_model_object(run.soar)
        case_data = soar_wrapper.get_case(case_id=run.case_id)
        if isinstance(case_data, dict) and "error" in case_data:
            return {
                "error": case_data["error"],
                "error_code": self._infer_error_code(case_data["error"]),
            }

        tasks_data = soar_wrapper.get_tasks(org_id=run.org_id, case_id=run.case_id)
        if isinstance(tasks_data, dict) and "error" in tasks_data:
            return {
                "error": tasks_data["error"],
                "error_code": self._infer_error_code(tasks_data["error"]),
            }

        generator = ActivityGenerator()
        generator.set_soarwrapper(soar_wrapper)
        for task in tasks_data.get("tasks", []):
            task_result = generator.generate_activity(
                case_title=case_data.get("title", ""),
                case_description=case_data.get("description", ""),
                task_data=task,
                web_search=bool(step.input_payload.get("use_web_search", False)),
                additional_notes=step.input_payload.get("additional_notes"),
            )
            if isinstance(task_result, dict) and "error" in task_result:
                return task_result

        return {"message": "success"}

    def _execute_investigation_step(self, run: WorkflowRun, step: WorkflowRunStep) -> dict:
        siem = run.siem or self.run_service.get_default_siem()
        if siem is None:
            return {
                "error": "No SIEM integration is available",
                "error_code": "soar_not_found",
            }

        investigator = Investigator(
            siem_id=siem.id,
            soar_id=run.soar_id,
            org_id=run.org_id,
            case_id=run.case_id,
            additional_notes=step.input_payload.get("additional_notes"),
            earliest_unit=step.input_payload.get("earliest_unit", "years"),
            earliest_magnitude=step.input_payload.get("earliest_magnitude", 1),
            vicinity_unit=step.input_payload.get("vicinity_unit", "hours"),
            vicinity_magnitude=step.input_payload.get("vicinity_magnitude", 1),
            max_iterations=step.input_payload.get("max_iterations", 3),
            max_queries_per_iteration=step.input_payload.get(
                "max_queries_per_iteration", 5
            ),
        )
        return investigator.investigate()

    def _execute_report_generation_step(self, run: WorkflowRun, step: WorkflowRunStep) -> dict:
        report_template = self.run_service.resolve_report_template(
            step.input_payload.get("report_template_id", "")
        )
        generator = ReportGenerator(
            soar_id=run.soar_id,
            org_id=run.org_id,
            case_id=run.case_id,
            report_template=report_template,
            additional_notes=step.input_payload.get("additional_notes"),
        )
        return generator.generate_report()

    def execute_step_adapter(self, run: WorkflowRun, step: WorkflowRunStep) -> dict:
        if step.step_name == WorkflowRun.StepName.TASK_GENERATION:
            return self._execute_task_generation_step(run, step)
        if step.step_name == WorkflowRun.StepName.ACTIVITY_GENERATION:
            return self._execute_activity_generation_step(run, step)
        if step.step_name == WorkflowRun.StepName.INVESTIGATION:
            return self._execute_investigation_step(run, step)
        if step.step_name == WorkflowRun.StepName.REPORT_GENERATION:
            return self._execute_report_generation_step(run, step)
        return {
            "error": f"Unknown step {step.step_name}",
            "error_code": "invalid_step_dependency",
        }

    def _finalize_failed_run(
        self,
        run: WorkflowRun,
        failing_step_name: str,
        error_code: str,
        error_message: str,
    ) -> None:
        run.status = WorkflowRun.Status.FAILED
        run.current_step = failing_step_name
        run.error_code = error_code
        run.error_message = error_message
        run.finished_at = django_timezone.now()
        run.save(
            update_fields=["status", "current_step", "error_code", "error_message", "finished_at"]
        )

    def _mark_remaining_steps_skipped(
        self, run: WorkflowRun, after_step_name: str, reason: str
    ) -> None:
        started = False
        for step_name in STEP_SEQUENCE:
            if step_name == after_step_name:
                started = True
                continue
            if not started:
                continue
            step = self.run_service.get_step_by_name(run, step_name)
            if step.status in {WorkflowRunStep.Status.SUCCEEDED, WorkflowRunStep.Status.FAILED}:
                continue
            step.status = WorkflowRunStep.Status.SKIPPED
            step.error_code = "upstream_disabled"
            step.error_message = reason
            step.finished_at = django_timezone.now()
            step.save(update_fields=["status", "error_code", "error_message", "finished_at"])

    def _previous_step_status_allows(self, step_index: int, run: WorkflowRun) -> bool:
        if step_index <= 0:
            return True
        previous_step = self.run_service.get_step_by_name(run, STEP_SEQUENCE[step_index - 1])
        return previous_step.status in {WorkflowRunStep.Status.SUCCEEDED, WorkflowRunStep.Status.SKIPPED}

    def _cleanup_workflow_run(self, run: WorkflowRun | None) -> None:
        if run is None:
            return
        try:
            run.delete()
        except Exception:
            logger.exception("Failed to delete workflow run run_id=%s", str(run.id))

    def execute_workflow_run(self, run_id: str) -> None:
        run = (
            WorkflowRun.objects.select_related("soar", "siem")
            .prefetch_related("steps", "events")
            .filter(id=run_id)
            .first()
        )
        if run is None:
            return
        if run.status in {
            WorkflowRun.Status.SUCCEEDED,
            WorkflowRun.Status.FAILED,
            WorkflowRun.Status.CANCELLED,
            WorkflowRun.Status.SKIPPED,
        }:
            self._cleanup_workflow_run(run)
            return
        if run.status not in {WorkflowRun.Status.QUEUED, WorkflowRun.Status.RUNNING}:
            return

        slot_key, token = self.acquire_workflow_slot(
            self.settings_service.get_singleton().max_concurrent_workflows
        )
        if slot_key is None:
            self.enqueue_workflow_run(run_id)
            return

        should_cleanup_run = False
        try:
            if run.status == WorkflowRun.Status.QUEUED:
                run.status = WorkflowRun.Status.RUNNING
                run.started_at = django_timezone.now()
                run.save(update_fields=["status", "started_at"])
            self.run_service.log_workflow_event(
                run, WorkflowEvent.Level.INFO, "workflow started", {"run_id": str(run.id)}
            )
            
            # Executes steps sequentially, if any step fails, the run is marked as failed and remaining steps are marked as skipped
            for index, step_name in enumerate(STEP_SEQUENCE):
                step = self.run_service.get_step_by_name(run, step_name)

                if run.status == WorkflowRun.Status.CANCELLED:
                    step.status = WorkflowRunStep.Status.CANCELLED
                    step.error_code = "cancelled"
                    step.error_message = run.cancel_reason or "Workflow cancelled"
                    step.finished_at = django_timezone.now()
                    step.save(update_fields=["status", "error_code", "error_message", "finished_at"])
                    continue

                if not step.enabled:
                    step.status = WorkflowRunStep.Status.SKIPPED
                    step.error_code = "disabled"
                    step.error_message = "Step disabled in workflow settings"
                    step.finished_at = django_timezone.now()
                    step.save(update_fields=["status", "error_code", "error_message", "finished_at"])
                    self.run_service.log_workflow_event(
                        run,
                        WorkflowEvent.Level.INFO,
                        f"{step_name} skipped",
                        step.input_payload,
                        step_name,
                    )
                    continue

                if not self._previous_step_status_allows(index, run):
                    step.status = WorkflowRunStep.Status.SKIPPED
                    step.error_code = "invalid_step_dependency"
                    step.error_message = "Previous step did not complete successfully"
                    step.finished_at = django_timezone.now()
                    step.save(update_fields=["status", "error_code", "error_message", "finished_at"])
                    self._finalize_failed_run(
                        run, step_name, step.error_code, step.error_message
                    )
                    self.run_service.log_workflow_event(
                        run,
                        WorkflowEvent.Level.ERROR,
                        "step dependency violation",
                        {"step_name": step_name},
                        step_name,
                    )
                    should_cleanup_run = True
                    return

                run.current_step = step_name
                run.save(update_fields=["current_step"])
                self.run_service.log_workflow_event(
                    run,
                    WorkflowEvent.Level.INFO,
                    f"{step_name} started",
                    step.input_payload,
                    step_name,
                )

                max_attempts = 2
                for attempt in range(1, max_attempts + 1):
                    step.attempt = attempt
                    if step.started_at is None:
                        step.started_at = django_timezone.now()
                    step.status = WorkflowRunStep.Status.RUNNING
                    step.save(update_fields=["attempt", "started_at", "status"])

                    # Executes step
                    result = self._normalize_step_result(self.execute_step_adapter(run, step))
                    
                    if result.get("ok"):
                        step.status = WorkflowRunStep.Status.SUCCEEDED
                        step.output_payload = result.get("payload", {})
                        step.error_code = ""
                        step.error_message = ""
                        step.finished_at = django_timezone.now()
                        step.save(
                            update_fields=[
                                "status",
                                "output_payload",
                                "error_code",
                                "error_message",
                                "finished_at",
                            ]
                        )
                        self.run_service.log_workflow_event(
                            run,
                            WorkflowEvent.Level.INFO,
                            f"{step_name} succeeded",
                            step.output_payload,
                            step_name,
                        )
                        break

                    step.error_code = result.get("error_code", "internal_error")
                    step.error_message = result.get("error_message", "Step execution failed")
                    if attempt < max_attempts and result.get("retryable"):
                        continue

                    step.status = WorkflowRunStep.Status.FAILED
                    step.finished_at = django_timezone.now()
                    step.save(update_fields=["status", "error_code", "error_message", "finished_at"])
                    self.run_service.log_workflow_event(
                        run,
                        WorkflowEvent.Level.ERROR,
                        f"{step_name} failed",
                        {
                            "error_code": step.error_code,
                            "error_message": step.error_message,
                        },
                        step_name,
                    )
                    self._finalize_failed_run(
                        run, step_name, step.error_code, step.error_message
                    )
                    self._mark_remaining_steps_skipped(run, step_name, step.error_message)
                    should_cleanup_run = True
                    return

            soar_wrapper = SOARWrapperBuilder().build_from_model_object(run.soar)
            case_data = soar_wrapper.get_case(case_id=run.case_id)
            soar_wrapper.update_case(
                case_id=run.case_id,
                title=f"{case_data.get('title', '')} (investigated)",
                description=f"{case_data.get('description', '')}\n\nThis case has been automatically investigated by ACI, please see the Case Report.",
            )

            if run.status != WorkflowRun.Status.CANCELLED:
                run.status = WorkflowRun.Status.SUCCEEDED
                run.finished_at = django_timezone.now()
                run.current_step = None
                run.save(update_fields=["status", "finished_at", "current_step"])
                self.run_service.log_workflow_event(
                    run,
                    WorkflowEvent.Level.INFO,
                    "workflow completed",
                    {"run_id": str(run.id)},
                )

            should_cleanup_run = True
        except Exception:
            should_cleanup_run = True
            raise

        finally:
            self.release_workflow_slot(slot_key, token)
            if should_cleanup_run:
                self._cleanup_workflow_run(run)
