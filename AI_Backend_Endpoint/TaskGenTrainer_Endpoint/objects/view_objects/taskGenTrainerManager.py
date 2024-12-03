from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from json import JSONDecodeError
import requests
import json

class CaseTemporaryStorageManager(APIView):
    def post(self, request, *args, **kwargs):
        """Modifies the already stored case data in redis

        JSON body format:
            ```json
            {
                "id": "...",
                "title": "...",
                "description": "...",
                "tasks" : [
                    {
                        "title": "...",
                        "description: "..."
                    },
                    ...
                ]
            }
            ```
            
        """
        try:
            response = requests.post(
                url=settings.AI_BACKEND_URL + "/task_generation_model/case_tmp_storage/",
                json=json.loads(request.body)
            )

            return Response(response.json(), status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
        except JSONDecodeError:
            return Response({"error": "Data not formatted properly"}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        try:
            id = request.data.get("id")
            response = requests.delete(
                url=settings.AI_BACKEND_URL + "/task_generation_model/case_tmp_storage/",
                data={"id": id}
            )

            return Response(response.json(), status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
        except JSONDecodeError:
            return Response({"error": "Data not formatted properly"}, status=status.HTTP_400_BAD_REQUEST)

class TaskGenTrainerManager(APIView):
    def post(self, request, *args, **kwargs):
        try:
            job_dict = job_scheduler.find_jobs(name="Model_Train")
            for job in job_dict["jobs"]:
                if job["status"] == "queued" or job["status"] == "running":
                    return Response({"error": "Only one training job is allowed to run a single time"}, status=status.HTTP_400_BAD_REQUEST)
            
            seed = request.POST.get("seed")
            max_steps = request.POST.get("max_steps")
            learning_rate = request.POST.get("learning_rate")
            gradient_accumulation_steps = request.POST.get("gradient_accumulation_steps")
            weight_decay = request.POST.get("weight_decay")
            
            if seed is None or max_steps is None or learning_rate is None or gradient_accumulation_steps is None or weight_decay is None:
                return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)
            
            form_data = {
                "seed": seed,
                "max_steps": max_steps,
                "learning_rate": learning_rate,
                "gradient_accumulation_steps": gradient_accumulation_steps,
                "weight_decay": weight_decay,
            }
            
            job_scheduler.add_job(
                requests.post,
                name="Model_Train",
                url=settings.AI_BACKEND_URL + "/task_generation_model/train_model/",
                data=form_data,
                timeout=None
            )

            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
    
class RestoreManager(APIView):
    def post(self, request, *args, **kwargs):
        try:
            job_dict = job_scheduler.find_jobs(name="Model_Reset")
            for job in job_dict["jobs"]:
                if job["status"] == "queued" or job["status"] == "running":
                    return Response({"error": "Only one resetting job is allowed to run a single time"}, status=status.HTTP_400_BAD_REQUEST)

            job_scheduler.add_job(
                requests.post,
                name="Model_Reset",
                url=settings.AI_BACKEND_URL + "/task_generation_model/restore_baseline/",
                timeout=None
            )

            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)