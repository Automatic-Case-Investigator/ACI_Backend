from django.http import JsonResponse
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler

def get_jobs(request):
    if request.method == "GET":
        jobs = job_scheduler.get_jobs()
        return JsonResponse(jobs)
    else:
        return JsonResponse({"error": "Invalid method"})