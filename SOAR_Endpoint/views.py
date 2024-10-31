from .objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from .objects.ai_systems.task_generator.task_generator import TaskGenerator
from django.shortcuts import render
from django.http import JsonResponse
from . import models


def add_soar_info(request):
    """Add new SOAR info to the database

    POST parameters:
        soar_type: SOAR type (Eg. TH for The Hive)
        api_key: SOAR API key
        protocol: SOAR protocol (Eg. http: or https:)
        hostname: SOAR host name (host and port)
        base_dir: SOAR url base directory

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "POST":
        soar_type = request.POST.get("soar_type")
        api_key = request.POST.get("api_key")
        protocol = request.POST.get("protocol")
        hostname = request.POST.get("hostname")
        base_dir = request.POST.get("base_dir")

        if soar_type is None:
            return JsonResponse({"error": "Required field missing"})
        if api_key is None:
            api_key = ""
        if protocol is None:
            protocol = ""
        if hostname is None:
            hostname = ""
        if base_dir is None:
            base_dir = ""

        try:
            models.SOARInfo(
                soar_type=soar_type,
                api_key=api_key,
                protocol=protocol,
                hostname=hostname,
                base_dir=base_dir,
            ).save()
            return JsonResponse({"message": "Success"})
        except ValueError:
            return JsonResponse({"error": "Invalid SOAR type"})
    else:
        return JsonResponse({"error": "Invalid method"})


def set_soar_info(request):
    """Set information of a SOAR in the database

    POST parameters:
        soar_id: SOAR id in the database
        soar_type: SOAR type (Eg. TH for The Hive)
        api_key: SOAR API key
        protocol: SOAR protocol (Eg. http: or https:)
        hostname: SOAR host name (host and port)
        base_dir: SOAR url base directory

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "POST":
        soar_id = request.POST.get("soar_id")
        soar_type = request.POST.get("soar_type")
        api_key = request.POST.get("api_key")
        protocol = request.POST.get("protocol")
        hostname = request.POST.get("hostname")
        base_dir = request.POST.get("base_dir")

        if soar_id is None or soar_type is None:
            return JsonResponse({"error": "Required field missing"})

        try:
            models.SOARInfo.objects.filter(id=soar_id).update(
                soar_type=soar_type,
                api_key=api_key,
                protocol=protocol,
                hostname=hostname,
                base_dir=base_dir,
            )
            return JsonResponse({"message": "Success"})
        except ValueError:
            return JsonResponse({"error": "Invalid SOAR type"})

    else:
        return JsonResponse({"error": "Invalid method"})


def get_case(request):
    """Get case data by case id

    GET parameters:
        soar_id: SOAR id in the database
        case_id: case id depending on the SOAR used

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "GET":
        soar_id = request.GET.get("soar_id")
        case_id = request.GET.get("case_id")

        if soar_id is None or case_id is None:
            return JsonResponse({"error": "Required field missing"})

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper_builder.setSOARType(soar_info_obj.soar_type)
        soar_wrapper_builder.setProtocol(soar_info_obj.protocol)
        soar_wrapper_builder.setHostname(soar_info_obj.hostname)
        soar_wrapper_builder.setBaseDir(soar_info_obj.base_dir)
        soar_wrapper_builder.setAPIKey(soar_info_obj.api_key)
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build()
        except TypeError as e:
            return JsonResponse({"error": str(e)})
            
        return JsonResponse(soar_wrapper.get_case(case_id))
    else:
        return JsonResponse({"error": "Invalid method"})

def generate_tasks(request):
    """Generate tasks for a specific case

    POST parameters:
        soar_id: SOAR id in the database
        case_id: case id depending on the SOAR used

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "POST":
        soar_id = request.POST.get("soar_id")
        case_id = request.POST.get("case_id")

        if soar_id is None or case_id is None:
            return JsonResponse({"error": "Required field missing"})

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper_builder.setSOARType(soar_info_obj.soar_type)
        soar_wrapper_builder.setProtocol(soar_info_obj.protocol)
        soar_wrapper_builder.setHostname(soar_info_obj.hostname)
        soar_wrapper_builder.setBaseDir(soar_info_obj.base_dir)
        soar_wrapper_builder.setAPIKey(soar_info_obj.api_key)
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build()
        except TypeError as e:
            return JsonResponse({"error": str(e)})
        
        case_data = soar_wrapper.get_case(case_id)
        
        try:
            task_generator = TaskGenerator()
            task_generator.set_soarwrapper(soarwrapper=soar_wrapper)
            task_generator.generate_task(case_data=case_data)
            
            return JsonResponse({"message": "Success"})
        except TypeError as e:
            return JsonResponse({"error": str(e)})
        
    else:
        return JsonResponse({"error": "Invalid method"})