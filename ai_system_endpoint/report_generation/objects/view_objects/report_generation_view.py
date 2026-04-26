from ai_system_endpoint.report_generation.objects.report_generator.report_generator import (
    ReportGenerator,
)
from ai_system_endpoint.agent_settings.models import AgentSettings
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class ReportGenerationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    REQUIRED_FIELDS = (
        "soar_id",
        "org_id",
        "case_id",
        "report_template_id",
    )

    def post(self, request, *args, **kwargs):
        data = request.data

        missing_fields = [f for f in self.REQUIRED_FIELDS if f not in data]
        empty_fields = [
            f
            for f in self.REQUIRED_FIELDS
            if f in data and str(data.get(f)).strip() == ""
        ]

        if missing_fields or empty_fields:
            return Response(
                {
                    "error": "Invalid parameters",
                    "missing_fields": missing_fields,
                    "empty_fields": empty_fields,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        soar_id = data.get("soar_id")
        org_id = data.get("org_id")
        case_id = data.get("case_id")
        report_template_id = str(data.get("report_template_id")).strip()

        settings_obj = AgentSettings.objects.filter(user=request.user).first()
        settings_templates = {}
        if settings_obj is not None and isinstance(settings_obj.report_templates, dict):
            settings_templates = settings_obj.report_templates

        if report_template_id not in settings_templates:
            return Response(
                {"error": 'Parameter "report_template_id" does not exist in user settings'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report_template = settings_templates.get(report_template_id)

        report_generator = ReportGenerator(
            soar_id=soar_id,
            org_id=org_id,
            case_id=case_id,
            report_template=report_template,
        )
        job_scheduler.add_job(
            report_generator.generate_report,
            name="Report_Generation",
        )

        return Response(
            {"message": "Success"},
            status=status.HTTP_200_OK,
        )
