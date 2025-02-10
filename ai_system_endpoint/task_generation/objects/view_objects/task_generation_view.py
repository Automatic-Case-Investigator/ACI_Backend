from ai_system_endpoint.task_generation.objects.task_generation.task_generator import TaskGenerator
from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from soar_endpoint import models
from django.conf import settings
from json import JSONDecodeError
import requests
import json

class TaskGenerationView(APIView):
    def post(self, request, *args, **kwargs):
        soar_id = request.POST.get("soar_id")
        case_id = request.POST.get("case_id")

        if soar_id is None or case_id is None:
            return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        case_data = None

        case_data = soar_wrapper.get_case(case_id)
        if "error" in case_data.keys():
            return Response(case_data, status=status.HTTP_400_BAD_REQUEST)
        
        case_data["title"] = case_data["title"][:settings.MAXIMUM_STRING_LENGTH]
        case_data["description"] = case_data["description"][:settings.MAXIMUM_STRING_LENGTH]

        try:
            task_generator = TaskGenerator()
            task_generator.set_soarwrapper(soarwrapper=soar_wrapper)
            job_scheduler.add_job(task_generator.generate_task, name="Task_Generation", case_data=case_data)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator for this problem."}, status=status.HTTP_502_BAD_GATEWAY)
        
        return Response({"message": "Success"}, status=status.HTTP_200_OK)

class CaseTemporaryStorageView(APIView):
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

class BackupView(APIView):
    def post(self, request):
        try:
            response = requests.post(url=settings.AI_BACKEND_URL + "/task_generation_model/backup/")
            return Response(response.json(), status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
        except JSONDecodeError:
            return Response({"error": "Data not formatted properly"}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        try:
            delete_name = request.data.get("hash")
            response = requests.delete(url=settings.AI_BACKEND_URL + "/task_generation_model/backup/", data={"hash": delete_name})
            return Response(response.json(), status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
        except JSONDecodeError:
            return Response({"error": "Data not formatted properly"}, status=status.HTTP_400_BAD_REQUEST)

class RollbackView(APIView):
    def post(self, request):
        try:
            restore_name = request.POST.get("hash")
            if restore_name is None:
                return Response({"error": "Data not formatted properly"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                response = requests.post(url=settings.AI_BACKEND_URL + "/task_generation_model/rollback/", data={"hash": restore_name})
                return Response(response.json(), status=status.HTTP_200_OK)        
            
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
        except JSONDecodeError:
            return Response({"error": "Data not formatted properly"}, status=status.HTTP_400_BAD_REQUEST)

class HistoryView(APIView):
    def get(self, request):
        try:
            page_number = int(request.GET.get("page"))
            response = requests.get(url=settings.AI_BACKEND_URL + f"/task_generation_model/history/?page={page_number}")
            return Response(response.json(), status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
        except JSONDecodeError:
            return Response({"error": "Data not formatted properly"}, status=status.HTTP_400_BAD_REQUEST)


class TaskGenTrainerView(APIView):
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
    
class RestoreView(APIView):
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
        
class CurrentBackupVersionView(APIView):
    def get(self, request):
        try:
            response = requests.get(url=settings.AI_BACKEND_URL + f"/task_generation_model/current_backup_version/")
            return Response(response.json(), status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator."}, status=status.HTTP_502_BAD_GATEWAY)
        except JSONDecodeError:
            return Response({"error": "Data not formatted properly"}, status=status.HTTP_400_BAD_REQUEST)