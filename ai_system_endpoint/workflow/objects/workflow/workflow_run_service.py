from __future__ import annotations

import hashlib
import uuid

from django.db import transaction
from django.utils import timezone as django_timezone

from ACI_Backend.utils.workflow_utils import trim_text
from ai_system_endpoint.models import (
    WorkflowEvent,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowSettings,
)
from ai_system_endpoint.workflow.objects.workflow.workflow_settings_service import (
    WorkflowSettingsService,
)
from siem_endpoint.models import SIEMInfo
from soar_endpoint.models import SOARInfo


STEP_SEQUENCE = [
    WorkflowRun.StepName.TASK_GENERATION,
    WorkflowRun.StepName.ACTIVITY_GENERATION,
    WorkflowRun.StepName.INVESTIGATION,
    WorkflowRun.StepName.REPORT_GENERATION,
]


class WorkflowRunService:
    def __init__(self, settings_service: WorkflowSettingsService):
        self.settings_service = settings_service

    def extract_external_event_id(self, payload: dict, raw_body: bytes | None = None) -> str:
        candidates = [
            payload.get("requestId"),
            payload.get("objectId"),
            payload.get("_id"),
        ]
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        candidates.extend(
            [
                details.get("_id"),
                details.get("requestId"),
                payload.get("context", {}).get("_id")
                if isinstance(payload.get("context"), dict)
                else None,
            ]
        )

        for candidate in candidates:
            if candidate is not None and str(candidate).strip() != "":
                return str(candidate)

        if raw_body:
            return hashlib.sha256(raw_body).hexdigest()
        return str(uuid.uuid4())

    def get_default_siem(self) -> SIEMInfo | None:
        return SIEMInfo.objects.order_by("id").first()

    def resolve_report_template(self, report_template_id: str) -> str:
        if not report_template_id:
            return ""

        from ai_system_endpoint.settings.models import AgentSettings

        for settings_obj in AgentSettings.objects.all():
            templates = (
                settings_obj.report_templates
                if isinstance(settings_obj.report_templates, dict)
                else {}
            )
            if report_template_id in templates:
                return templates[report_template_id]

        return report_template_id

    def get_step_by_name(self, run: WorkflowRun, step_name: str) -> WorkflowRunStep:
        return run.steps.get(step_name=step_name)

    def create_workflow_run(
        self,
        *,
        external_event_id: str | None,
        source: str,
        soar: SOARInfo,
        siem: SIEMInfo | None,
        org_id: str,
        case_id: str,
        settings_obj: WorkflowSettings,
        settings_snapshot: dict,
        raw_payload: dict,
        correlation_id: str,
    ) -> tuple[WorkflowRun, bool]:
        with transaction.atomic():
            if external_event_id is not None:
                existing = (
                    WorkflowRun.objects.select_for_update()
                    .filter(external_event_id=external_event_id)
                    .first()
                )
                if existing is not None:
                    return existing, False

            run = WorkflowRun.objects.create(
                external_event_id=external_event_id,
                source=source,
                soar=soar,
                siem=siem,
                org_id=org_id,
                case_id=case_id,
                status=(
                    WorkflowRun.Status.SKIPPED
                    if not settings_obj.enabled
                    else WorkflowRun.Status.QUEUED
                ),
                settings_snapshot=settings_snapshot,
                raw_payload=raw_payload,
                correlation_id=correlation_id,
            )

            for step_name in STEP_SEQUENCE:
                if step_name == WorkflowRun.StepName.TASK_GENERATION:
                    enabled = settings_obj.task_generation_enabled
                elif step_name == WorkflowRun.StepName.ACTIVITY_GENERATION:
                    enabled = settings_obj.activity_generation_enabled
                elif step_name == WorkflowRun.StepName.INVESTIGATION:
                    enabled = settings_obj.investigation_enabled
                else:
                    enabled = settings_obj.report_generation_enabled

                step_status = (
                    WorkflowRunStep.Status.PENDING
                    if settings_obj.enabled and enabled
                    else WorkflowRunStep.Status.SKIPPED
                )
                WorkflowRunStep.objects.create(
                    workflow_run=run,
                    step_name=step_name,
                    enabled=settings_obj.enabled and enabled,
                    status=step_status,
                    attempt=0,
                    input_payload=self.settings_service.build_step_input_payload(
                        settings_snapshot, step_name
                    ),
                )

            if not settings_obj.enabled:
                run.current_step = None
                run.finished_at = django_timezone.now()
                run.save(update_fields=["current_step", "finished_at", "status"])

            return run, True

    def log_workflow_event(
        self,
        run: WorkflowRun,
        level: str,
        message: str,
        payload: dict | None = None,
        step_name: str = "",
    ) -> None:
        WorkflowEvent.objects.create(
            workflow_run=run,
            step_name=step_name,
            level=level,
            message=message,
            payload=payload or {},
            correlation_id=run.correlation_id,
        )

    def serialize_step(self, step: WorkflowRunStep) -> dict:
        return {
            "step_name": step.step_name,
            "enabled": step.enabled,
            "status": step.status,
            "attempt": step.attempt,
            "input_payload": step.input_payload,
            "output_payload": step.output_payload,
            "error_code": step.error_code or None,
            "error_message": step.error_message or None,
            "started_at": (
                step.started_at.isoformat().replace("+00:00", "Z")
                if step.started_at
                else None
            ),
            "finished_at": (
                step.finished_at.isoformat().replace("+00:00", "Z")
                if step.finished_at
                else None
            ),
        }

    def serialize_run(self, run: WorkflowRun) -> dict:
        steps = sorted(
            list(run.steps.all()), key=lambda item: STEP_SEQUENCE.index(item.step_name)
        )
        events = list(run.events.all().order_by("created_at"))
        return {
            "id": str(run.id),
            "external_event_id": run.external_event_id,
            "source": run.source,
            "soar_id": str(run.soar_id) if run.soar_id else None,
            "org_id": run.org_id,
            "case_id": run.case_id,
            "status": run.status,
            "current_step": run.current_step,
            "error_code": run.error_code or None,
            "error_message": run.error_message or None,
            "correlation_id": run.correlation_id,
            "created_at": (
                run.created_at.isoformat().replace("+00:00", "Z")
                if run.created_at
                else None
            ),
            "started_at": (
                run.started_at.isoformat().replace("+00:00", "Z")
                if run.started_at
                else None
            ),
            "finished_at": (
                run.finished_at.isoformat().replace("+00:00", "Z")
                if run.finished_at
                else None
            ),
            "steps": [self.serialize_step(step) for step in steps],
            "events": [
                {
                    "level": event.level,
                    "step_name": event.step_name or None,
                    "message": event.message,
                    "payload": event.payload,
                    "created_at": (
                        event.created_at.isoformat().replace("+00:00", "Z")
                        if event.created_at
                        else None
                    ),
                }
                for event in events
            ],
        }

    def cancel_workflow_run(self, run: WorkflowRun, reason: str) -> bool:
        if run.status in {
            WorkflowRun.Status.SUCCEEDED,
            WorkflowRun.Status.FAILED,
            WorkflowRun.Status.CANCELLED,
            WorkflowRun.Status.SKIPPED,
        }:
            return False

        run.status = WorkflowRun.Status.CANCELLED
        run.cancel_reason = trim_text(reason, 2000)
        run.finished_at = django_timezone.now()
        run.save(update_fields=["status", "cancel_reason", "finished_at"])

        for step in run.steps.all():
            if step.status in {WorkflowRunStep.Status.SUCCEEDED, WorkflowRunStep.Status.FAILED}:
                continue
            step.status = WorkflowRunStep.Status.CANCELLED
            step.error_code = "cancelled"
            step.error_message = run.cancel_reason or "Workflow cancelled"
            step.finished_at = django_timezone.now()
            step.save(
                update_fields=["status", "error_code", "error_message", "finished_at"]
            )

        self.log_workflow_event(
            run,
            WorkflowEvent.Level.WARNING,
            "workflow cancelled",
            {"reason": run.cancel_reason},
        )
        return True
