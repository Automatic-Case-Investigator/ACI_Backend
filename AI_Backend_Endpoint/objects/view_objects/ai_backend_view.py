from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import requests

class StatusView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            response = requests.get(url=settings.AI_BACKEND_URL + "test_connection/")
            data = response.json()
            if data["message"] == "Success":
                return Response({"message": "Success", "connected": True}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Success", "connected": False}, status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"message": "Success", "connected": False}, status=status.HTTP_200_OK)
        except requests.exceptions.JSONDecodeError:
            return Response({"message": "Success", "connected": False}, status=status.HTTP_200_OK)