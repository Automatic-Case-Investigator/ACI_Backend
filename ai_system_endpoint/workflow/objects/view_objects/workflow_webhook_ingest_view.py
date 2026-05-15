import json
import hmac

from django.conf import settings
from django.utils import timezone as django_timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from ai_system_endpoint.models import WorkflowRun
from ai_system_endpoint.workflow.utils.utils import error_response
from ai_system_endpoint.workflow.services import (
    workflow_execution_service,
    workflow_run_service,
    workflow_settings_service,
)


class WorkflowWebhookIngestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def _extract_bearer_token(self, authorization_header: str | None) -> str:
        if not authorization_header:
            return ""
        scheme, _, token = authorization_header.strip().partition(" ")
        if scheme.lower() != "bearer" or not token:
            return ""
        return token.strip()

    def post(self, request, *args, **kwargs):
        correlation_id = request.headers.get("X-Correlation-Id") or f"req_{django_timezone.now().timestamp():.0f}"
        raw_body = request.body or b"{}"
        settings_obj = workflow_settings_service.get_singleton()

        configured_bearer_key = (
            settings_obj.webhook_bearer_key or settings.WORKFLOW_WEBHOOK_SECRET or ""
        ).strip()
        if not configured_bearer_key:
            return error_response(
                code="webhook_auth_not_configured",
                message="Webhook bearer authentication is not configured",
                correlation_id=correlation_id,
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        request_bearer_token = self._extract_bearer_token(
            request.headers.get("Authorization")
        )
        if not request_bearer_token or not hmac.compare_digest(
            request_bearer_token, configured_bearer_key
        ):
            return error_response(
                code="unauthorized",
                message="Invalid or missing bearer token",
                correlation_id=correlation_id,
                http_status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return error_response(
                code="validation_error",
                message="Malformed webhook payload",
                correlation_id=correlation_id,
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if payload.get("action") not in {"create", "case_created"}:
            return error_response(
                code="validation_error",
                message="Webhook payload is not a case-create event",
                correlation_id=correlation_id,
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        details = payload.get("details") if isinstance(payload.get("details"), dict) else payload.get("context") if isinstance(payload.get("context"), dict) else payload.get("object")
        if not isinstance(details, dict):
            details = payload.get("details") if isinstance(payload.get("details"), dict) else {}

        case_id = str(details.get("_id") or payload.get("objectId") or payload.get("rootId") or "").strip()
        org_id = str((payload.get("organisation") or {}).get("organisationId") or (payload.get("organisation") or {}).get("organisation") or "").strip()
        if not case_id or not org_id:
            return error_response(
                code="validation_error",
                message="Webhook payload missing case or organization identifiers",
                details={"case_id": ["Required"], "org_id": ["Required"]},
                correlation_id=correlation_id,
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if not settings_obj.enabled:
            return Response(
                {
                    "accepted": True,
                    "skipped": True,
                    "status": "automatic_workflow_disabled",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        settings_snapshot = workflow_settings_service.build_snapshot(settings_obj)
        external_event_id = workflow_run_service.extract_external_event_id(payload, raw_body)
        soar = settings_obj.soar
        if soar is None:
            return error_response(
                code="soar_not_found",
                message="Workflow settings do not reference a SOAR integration",
                correlation_id=correlation_id,
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        siem = settings_obj.siem or workflow_run_service.get_default_siem()
        if settings_obj.investigation_enabled and siem is None:
            return error_response(
                code="validation_error",
                message="No SIEM integration is available for the investigation step",
                correlation_id=correlation_id,
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        run, created = workflow_run_service.create_workflow_run(
            external_event_id=external_event_id,
            source="soar_webhook",
            soar=soar,
            siem=siem,
            org_id=org_id,
            case_id=case_id,
            settings_obj=settings_obj,
            settings_snapshot=settings_snapshot,
            raw_payload=payload,
            correlation_id=correlation_id,
        )

        if created and run.status == WorkflowRun.Status.QUEUED:
            job_scheduler.add_job(
                workflow_execution_service.execute_workflow_run,
                name="Automatic_Workflow",
                run_id=str(run.id),
            )

        return Response(
            {
                "accepted": True,
                "scheduled": bool(created and run.status == WorkflowRun.Status.QUEUED),
            },
            status=status.HTTP_202_ACCEPTED,
        )
