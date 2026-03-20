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
    
    REQUIRED_FIELDS = (
        "siem_id",
        "soar_id",
        "org_id",
        "case_id",
        "earliest_magnitude",
        "earliest_unit",
        "vicinity_magnitude",
        "vicinity_unit",
        "max_iterations",
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
                    "empty_fields": empty_fields
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        siem_id = data.get("siem_id")
        soar_id = data.get("soar_id")
        org_id = data.get("org_id")
        case_id = data.get("case_id")
        
        if not data.get("earliest_magnitude").isdigit():
            return Response(
                {
                    "error": 'Parameter "earliest_magnitude" is not an integer'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if not data.get("vicinity_magnitude").isdigit():
            return Response(
                {
                    "error": 'Parameter "vicinity_magnitude" is not an integer'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if not data.get("max_iterations").isdigit():
            return Response(
                {
                    "error": 'Parameter "max_iterations" is not an integer'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        earliest_unit = data.get("earliest_unit")
        earliest_magnitude = int(data.get("earliest_magnitude"))
        vicinity_unit = data.get("vicinity_unit")
        vicinity_magnitude = int(data.get("vicinity_magnitude"))
        max_iterations = int(data.get("max_iterations"))
            
        valid_units = [
            "hours",
            "days",
            "weeks",
            "months",
            "years",
        ]
        if earliest_unit not in valid_units:
            return Response(
                {
                    "error": f'earliest_unit: "{earliest_unit}" is not a valid unit'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        if vicinity_unit not in valid_units:
            return Response(
                {
                    "error": f'vicinity_unit: "{vicinity_unit}" is not a valid unit'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if earliest_magnitude <= 0:
            earliest_magnitude = 1
            
        if max_iterations > 20:
            max_iterations = 20
        elif max_iterations <= 0:
            max_iterations = 1
        
        investigator = Investigator(
            siem_id=siem_id,
            soar_id=soar_id,
            org_id=org_id,
            case_id=case_id,
            earliest_unit=earliest_unit,
            earliest_magnitude=earliest_magnitude,
            vicinity_unit=vicinity_unit,
            vicinity_magnitude=vicinity_magnitude,
            max_iterations=max_iterations
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
