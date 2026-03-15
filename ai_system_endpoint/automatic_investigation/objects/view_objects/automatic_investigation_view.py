from ai_system_endpoint.automatic_investigation.objects.investigator.investigator import (
    Investigator,
)
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

class AutomaticInvestigationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        siem_id = request.POST.get("siem_id")
        soar_id = request.POST.get("soar_id")
        org_id = request.POST.get("org_id")
        case_id = request.POST.get("case_id")

        investigator = Investigator(
            siem_id=siem_id,
            soar_id=soar_id,
            org_id=org_id,
            case_id=case_id
        )

        # Add to job queue for investigation
        job_scheduler.add_job(
            investigator.investigate,
            name="Case_Investigation",
        )

        return Response(
            {"message": "Success"},
            status=status.HTTP_200_OK,
        )
