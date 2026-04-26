from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ai_system_endpoint.agent_settings.models import AgentSettings


class AgentSettingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _serialize(self, obj: AgentSettings) -> dict:
        templates = obj.report_templates if isinstance(obj.report_templates, dict) else {}

        return {
            "report_templates": templates,
            "updated_at": obj.updated_at,
        }

    def get(self, request, *args, **kwargs):
        settings_obj, _ = AgentSettings.objects.get_or_create(
            user=request.user,
        )

        return Response(
            {
                "message": "Success",
                "settings": self._serialize(settings_obj),
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):
        return self._update(request)

    def patch(self, request, *args, **kwargs):
        return self._update(request)

    def _update(self, request):
        data = request.data

        settings_obj, _ = AgentSettings.objects.get_or_create(
            user=request.user,
        )

        if "report_templates" in data:
            value = data.get("report_templates")
            if not isinstance(value, dict):
                return Response(
                    {"error": 'Parameter "report_templates" must be an object'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for key, template in value.items():
                if not isinstance(key, str) or not isinstance(template, str):
                    return Response(
                        {"error": 'Each entry in "report_templates" must be string:string'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            settings_obj.report_templates = value
        else:
            return Response(
                {"error": 'Parameter "report_templates" is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        settings_obj.save()

        return Response(
            {
                "message": "Success",
                "settings": self._serialize(settings_obj),
            },
            status=status.HTTP_200_OK,
        )
