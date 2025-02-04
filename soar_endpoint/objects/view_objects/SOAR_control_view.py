from soar_endpoint.objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from soar_endpoint import models
from django.conf import settings

class OrgControlView(APIView):
    def get(self, request, *args, **kwargs):
        soar_id = request.GET.get("soar_id")
        
        # if user does not provide the argument
        if soar_id is None:
            return Response({"error": "Target SOAR id not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        # if corresponding SOAR data entry doesn't exist
        target_soar = models.SOARInfo.objects.get(id=soar_id)
        if target_soar is None:
            return Response({"error": "Target SOAR id not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=target_soar)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        org_data = soar_wrapper.get_organizations()
        if "error" in org_data.keys():
            return Response(org_data, status=status.HTTP_502_BAD_GATEWAY)

        return Response(org_data, status=status.HTTP_200_OK)

class CaseControlView(APIView):
    def get(self, request, *args, **kwargs):
        soar_id = request.GET.get("soar_id")
        case_id = request.GET.get("case_id")
        org_id = request.GET.get("org_id")
        search_str = request.GET.get("search")
        time_sort_type = request.GET.get("time_sort_type")
        page_number = request.GET.get("page")

        if soar_id is None or (case_id is None and org_id is None):
            return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        if case_id is not None:
            case_data = soar_wrapper.get_case(case_id)
            if "error" in case_data.keys():
                return Response(case_data, status=status.HTTP_502_BAD_GATEWAY)

            return Response(case_data, status=status.HTTP_200_OK)
        else:
            cases_data = None
            
            if page_number is not None and not page_number.isdigit():
                return Response({"error": "Invalid page number"}, status=status.HTTP_400_BAD_REQUEST)
            elif page_number is not None:
                page_number = int(page_number)
                
            if time_sort_type is not None and not time_sort_type.isdigit():
                return Response({"error": "Invalid time sort type"}, status=status.HTTP_400_BAD_REQUEST)
            elif time_sort_type is not None:
                time_sort_type = int(time_sort_type)

            cases_data = soar_wrapper.get_cases(org_id, search_str, settings.CASE_PAGE_SIZE, time_sort_type, page_number)
            
            if "error" in cases_data.keys():
                return Response(cases_data, status=status.HTTP_502_BAD_GATEWAY)
            
            return Response(cases_data, status=status.HTTP_200_OK)
        
class TaskControlView(APIView):
    def get(self, request, *args, **kwargs):
        soar_id = request.GET.get("soar_id")
        org_id = request.GET.get("org_id")
        task_id = request.GET.get("task_id")
        case_id = request.GET.get("case_id")

        if soar_id is None or (task_id is None and case_id is None):
            return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        if task_id is not None:
            task_data = soar_wrapper.get_task(org_id, task_id)
            if "error" in task_data.keys():
                return Response(task_data, status=status.HTTP_502_BAD_GATEWAY)

            return Response(task_data, status=status.HTTP_200_OK)
        else:
            tasks_data = soar_wrapper.get_tasks(org_id, case_id)
            if "error" in tasks_data.keys():
                return Response(tasks_data, status=status.HTTP_502_BAD_GATEWAY)

            return Response(tasks_data, status=status.HTTP_200_OK)
        
    def delete(self, request, *args, **kwargs):
        soar_id = request.data.get("soar_id")
        task_id = request.data.get("task_id")

        if soar_id is None or task_id is None:
            return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response = soar_wrapper.delete_task(task_id)
        if "error" in response.keys():
            return Response(response, status=status.HTTP_502_BAD_GATEWAY)

        return Response(response, status=status.HTTP_200_OK)
    
class TaskLogControlView(APIView):
    def get(self, request, *args, **kwargs):
        soar_id = request.GET.get("soar_id")
        task_id = request.GET.get("task_id")

        if soar_id is None or task_id is None:
            return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        task_logs_data = soar_wrapper.get_task_logs(task_id)
        if "error" in task_logs_data.keys():
            return Response(task_logs_data, status=status.HTTP_502_BAD_GATEWAY)

        return Response(task_logs_data, status=status.HTTP_200_OK)