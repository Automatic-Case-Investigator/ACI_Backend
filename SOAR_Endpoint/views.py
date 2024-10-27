from django.shortcuts import render
from django.http import JsonResponse
from .objects.soar_wrapper.soar_wrapper_builder import SOARWrapperBuilder
from . import models


def add_soar_info(request):
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
    if request.method == "POST":
        soar_id = request.POST.get("soar_id")
        soar_type = request.POST.get("soar_type")
        api_key = request.POST.get("api_key")
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
        soar_wrapper = soar_wrapper_builder.build()
        
        if soar_wrapper == None:
            # Todo: return more detailed description
            return JsonResponse({"error": "Missing required information for SOAR"})
        
        print(type(soar_wrapper))
            
        return JsonResponse({"message": "Hello"})
    else:
        return JsonResponse({"error": "Invalid method"})
