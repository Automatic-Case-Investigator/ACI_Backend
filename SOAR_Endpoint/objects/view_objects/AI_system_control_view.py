from SOAR_Endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from ACI_Backend.objects.ai_systems.task_generator.task_generator import TaskGenerator
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from SOAR_Endpoint import models
import requests

class TaskGeneratorControlView(APIView):
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

        try:
            task_generator = TaskGenerator()
            task_generator.set_soarwrapper(soarwrapper=soar_wrapper)
            job_scheduler.add_job(task_generator.generate_task, name="Task_Generation", case_data=case_data)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except requests.exceptions.ConnectionError:
            return Response({"error": "Unable to connect to the AI backend. Please contact the administrator for this problem."}, status=status.HTTP_502_BAD_GATEWAY)
        
        return Response({"message": "Success"}, status=status.HTTP_200_OK)