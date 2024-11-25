from ACI_Backend.objects.job_scheduler.job_scheduler import job_scheduler
from django.http import JsonResponse
from django.conf import settings
from json import JSONDecodeError
import requests
import json

def add_case_data(request):
    """Stores case data temporarily in redis

    POST JSON body format:
        ```json
        {
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
        

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "POST":
        try:
            response = requests.post(
                url=settings.AI_BACKEND_URL + "task_generation_model/add_case_data/",
                json=json.loads(request.body)
            )

            return JsonResponse(response.json())
        except requests.exceptions.ConnectionError:
            return JsonResponse({"error": "Unable to connect to the AI backend. Please contact the administrator."})
        except JSONDecodeError:
            return JsonResponse({"error": "Data not formatted properly"})
    
    else:
        return JsonResponse({"error": "Invalid method"})
    
def set_case_data(request):
    """Modifies the already stored case data in redis

    POST JSON body format:
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
        

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "POST":
        try:
            response = requests.post(
                url=settings.AI_BACKEND_URL + "/task_generation_model/set_case_data",
                json=json.loads(request.body)
            )

            return JsonResponse(response.json())
        except requests.exceptions.ConnectionError:
            return JsonResponse({"error": "Unable to connect to the AI backend. Please contact the administrator."})
        except JSONDecodeError:
            return JsonResponse({"error": "Data not formatted properly"})
    
    else:
        return JsonResponse({"error": "Invalid method"})
    
def delete_case_data(request):
    """Removes case data redis

    POST parameters:
        id: case data id

    Args:
        request (_type_): django request

    Returns:
        JsonResponse: Json response
    """
    if request.method == "POST":
        try:
            response = requests.post(
                url=settings.AI_BACKEND_URL + "/task_generation_model/delete_case_data",
                json=json.loads(request.body)
            )

            return JsonResponse(response.json())
        except requests.exceptions.ConnectionError:
            return JsonResponse({"error": "Unable to connect to the AI backend. Please contact the administrator."})
        except JSONDecodeError:
            return JsonResponse({"error": "Data not formatted properly"})
    
    else:
        return JsonResponse({"error": "Invalid method"})

def train_model(request):
    if request.method == "POST":
        try:
            job_scheduler.add_job(requests.post, name="Model_Train", url=settings.AI_BACKEND_URL + "/task_generation_model/train_model/", timeout=None)

            return JsonResponse({"message": "Success"})
        except requests.exceptions.ConnectionError:
            return JsonResponse({"error": "Unable to connect to the AI backend. Please contact the administrator."})
    
    else:
        return JsonResponse({"error": "Invalid method"})