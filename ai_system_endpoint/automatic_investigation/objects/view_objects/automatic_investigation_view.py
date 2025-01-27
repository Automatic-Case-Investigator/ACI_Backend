from ai_system_endpoint.automatic_investigation.objects.investigator.investigator import (
    Investigator,
)
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
import json


class AutomaticInvestigationView(APIView):
    def post(self, request, *args, **kwargs):
        soar_id = request.POST.get("soar_id")
        org_id = request.POST.get("org_id")
        case_id = request.POST.get("case_id")
        generate_activities = request.POST.get("generate_activities")
        investigate_siem = request.POST.get("investigate_siem")

        # Verify the parameters
        if case_id is None:
            return Response(
                {"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST
            )

        if generate_activities is None:
            generate_activities = False
        elif generate_activities.isdigit():
            return Response(
                {"error": 'Parameter "generate_activities" not formatted properly'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            generate_activities = bool(int(generate_activities))

        if investigate_siem is None:
            investigate_siem = False
        elif investigate_siem.isdigit():
            return Response(
                {"error": 'Parameter "investigate_siem" not formatted properly'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            investigate_siem = bool(int(investigate_siem))

        investigator = Investigator(
            soar_id=soar_id,
            org_id=org_id,
            case_id=case_id,
            generate_activities=generate_activities,
            investigate_siem=investigate_siem,
        )

        # Add to job queue for investigation
        job_scheduler.add_job(
            investigator.investigate(),
            name="Case_Investigation",
        )

        return Response(
            {"message": "Success"},
            status=status.HTTP_200_OK,
        )