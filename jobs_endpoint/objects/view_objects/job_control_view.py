from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

class JobControlView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        jobs = job_scheduler.get_jobs()
        return Response(jobs, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        job_id = request.data.get("job_id")
        if job_id is None:
            return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)
        
        success = job_scheduler.remove_job(job_id)
        if success:
            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        
        return Response({"error": "Failed to remove job"}, status=status.HTTP_200_OK)