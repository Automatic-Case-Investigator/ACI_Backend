from .objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from .objects.ai_systems.task_generator.task_generator import TaskGenerator
from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from django.shortcuts import render
from django.http import JsonResponse
from . import models
import requests


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
        name = request.POST.get("name")
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
                name=name,
                hostname=hostname,
                base_dir=base_dir,
            ).save()
            return JsonResponse({"message": "Success"})
        except ValueError:
            return JsonResponse({"error": "Invalid SOAR type"})
    else:
        return JsonResponse({"error": "Invalid method"})

def get_soars_info(request):
    if request.method == "GET":
        soar_objs = models.SOARInfo.objects.all()
        output = {"message": []}
        
        for soar in soar_objs:
            output["message"].append({
                "id": soar.id,
                "soar_type" : soar.soar_type,
                "api_key": soar.api_key,
                "protocol": soar.protocol,
                "hostname": soar.hostname,
                "base_dir": soar.base_dir,
                "name": soar.name
            })
        
        return JsonResponse(output)
    else:
        return JsonResponse({"error": "Invalid method"})

def delete_soar_info(request):
    if request.method == "POST":
        soar_id = request.POST.get("soar_id")

        if soar_id is None:
            return JsonResponse({"error": "Required field missing"})
        
        models.SOARInfo.objects.filter(id=soar_id).delete()
        
        return JsonResponse({"message": "Success"})
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
        name = request.POST.get("name")
        hostname = request.POST.get("hostname")
        base_dir = request.POST.get("base_dir")

        if soar_id is None:
            return JsonResponse({"error": "Required field missing"})

        try:
            if soar_type is not None:
                models.SOARInfo.objects.filter(id=soar_id).update(soar_type=soar_type)
            if api_key is not None:
                models.SOARInfo.objects.filter(id=soar_id).update(api_key=api_key)
            if protocol is not None:
                models.SOARInfo.objects.filter(id=soar_id).update(protocol=protocol)
            if name is not None:
                models.SOARInfo.objects.filter(id=soar_id).update(name=name)
            if hostname is not None:
                models.SOARInfo.objects.filter(id=soar_id).update(hostname=hostname)
            if base_dir is not None:
                models.SOARInfo.objects.filter(id=soar_id).update(base_dir=base_dir)
            return JsonResponse({"message": "Success"})
        except ValueError:
            return JsonResponse({"error": "Invalid SOAR type"})

    else:
        return JsonResponse({"error": "Invalid method"})

def get_organizations(request):
    """List all organizations visible to the user

    GET parameters:
        soar_id: SOAR id in the database

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "GET":
        soar_id = request.GET.get("soar_id")
        
        # if user does not provide the argument
        if soar_id is None:
            return JsonResponse({"error": "Target SOAR id not found"})
        
        # if corresponding SOAR data entry doesn't exist
        target_soar = models.SOARInfo.objects.get(id=soar_id)
        if target_soar is None:
            return JsonResponse({"error": "Target SOAR id not found"})
        
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=target_soar)
        except TypeError as e:
            return JsonResponse({"error": str(e)})
        
        return JsonResponse(soar_wrapper.get_organizations())

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
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return JsonResponse({"error": str(e)})

        return JsonResponse(soar_wrapper.get_case(case_id))
    else:
        return JsonResponse({"error": "Invalid method"})
    
def get_cases(request):
    """List all cases in the organization

    GET parameters:
        soar_id: SOAR id in the database
        org_id: organization id depending on the SOAR used

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "GET":
        soar_id = request.GET.get("soar_id")
        org_id = request.GET.get("org_id")

        if soar_id is None or org_id is None:
            return JsonResponse({"error": "Required field missing"})

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        soar_wrapper = None
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return JsonResponse({"error": str(e)})

        return JsonResponse(soar_wrapper.get_cases(org_id))
    else:
        return JsonResponse({"error": "Invalid method"})

def get_tasks(request):
    """Get tasks for a specific case

    POST parameters:
        soar_id: SOAR id in the database
        org_id: organization id depending on the SOAR used
        case_id: case id depending on the SOAR used

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "GET":
        soar_id = request.GET.get("soar_id")
        org_id = request.GET.get("org_id")
        case_id = request.GET.get("case_id")

        if soar_id is None or org_id is None or case_id is None:
            return JsonResponse({"error": "Required field missing"})

        soar_info_obj = models.SOARInfo.objects.get(id=soar_id)
        soar_wrapper_builder = SOARWrapperBuilder()
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return JsonResponse({"error": str(e)})

        return JsonResponse(soar_wrapper.get_tasks(org_id, case_id))
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
        try:
            soar_wrapper = soar_wrapper_builder.build_from_model_object(soar_info_obj=soar_info_obj)
        except TypeError as e:
            return JsonResponse({"error": str(e)})

        case_data = None

        try:
            case_data = soar_wrapper.get_case(case_id)
        except requests.exceptions.ConnectionError:
            return JsonResponse({"error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."})
        
        try:
            task_generator = TaskGenerator()
            task_generator.set_soarwrapper(soarwrapper=soar_wrapper)
            job_scheduler.add_job(task_generator.generate_task, case_data=case_data)
        except TypeError as e:
            return JsonResponse({"error": str(e)})
        except requests.exceptions.ConnectionError:
            return JsonResponse({"error": "Unable to connect to the AI backend. Please contact the administrator for this problem."})
        
        return JsonResponse({"message": "Success"})
    else:
        return JsonResponse({"error": "Invalid method"})
