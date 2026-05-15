from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ai_system_endpoint.workflow.utils.utils import error_response
from ai_system_endpoint.workflow.services import (
    workflow_settings_service,
)


class WorkflowSettingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        settings_obj = workflow_settings_service.get_singleton()
        return Response(
            {
                "settings": workflow_settings_service.serialize(settings_obj),
                "updated_at": settings_obj.updated_at.isoformat().replace("+00:00", "Z"),
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):
        normalized, errors = workflow_settings_service.normalize_payload(request.data)
        if errors:
            return error_response(
                code="validation_error",
                message="Invalid workflow settings",
                details=errors,
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        settings_obj = workflow_settings_service.get_singleton()
        workflow_settings_service.save(settings_obj, normalized, updated_by=request.user)

        return Response(
            {
                "settings": workflow_settings_service.serialize(settings_obj),
                "updated_at": settings_obj.updated_at.isoformat().replace("+00:00", "Z"),
            },
            status=status.HTTP_200_OK,
        )
