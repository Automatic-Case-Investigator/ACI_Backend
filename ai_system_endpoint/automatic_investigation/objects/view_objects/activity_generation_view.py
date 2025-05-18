from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
import requests

class RestoreView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        try:
            job_dict = job_scheduler.find_jobs(name="Model_Reset")
            for job in job_dict["jobs"]:
                if job["status"] == "queued" or job["status"] == "running":
                    return Response({"error": "Only one resetting job is allowed to run a single time"}, status=status.HTTP_400_BAD_REQUEST)

            job_scheduler.add_job(
                requests.post,
                name="Model_Reset",
                url=settings.AI_BACKEND_URL + "/activity_generation_model/restore_baseline/",
                timeout=None
            )

            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
        