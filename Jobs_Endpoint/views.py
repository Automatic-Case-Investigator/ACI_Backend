from django.http import JsonResponse
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler

def get_jobs(request):
    if request.method == "GET":
        jobs = job_scheduler.get_jobs()
        return JsonResponse(jobs)
    else:
        return JsonResponse({"error": "Invalid method"})
    
def remove_job(request):
    if request.method == "POST":
        job_id = request.POST.get("job_id")
        if job_id is None:
            return JsonResponse({"error": "Required field missing"})
        
        
        success = job_scheduler.remove_job(job_id)
        if success:
            return JsonResponse({"message": "Success"})
        
        return JsonResponse({"error": "Failed to remove job"})
    else:
        return JsonResponse({"error": "Invalid method"})