from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
import requests

class StatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        try:
            response = requests.get(
                url=settings.AI_BACKEND_URL + "test_connection/",
                headers={
                    "Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"
                }
            )
            data = response.json()
            
            if response.status_code != 200:
                return Response({"message": "Success", "connected": False}, status=status.HTTP_200_OK)
                        
            if data["message"] == "Success":
                return Response({"message": "Success", "connected": True}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Success", "connected": False}, status=status.HTTP_200_OK)
        except requests.exceptions.ConnectionError:
            return Response({"message": "Success", "connected": False}, status=status.HTTP_200_OK)
        except requests.exceptions.JSONDecodeError:
            return Response({"message": "Success", "connected": False}, status=status.HTTP_200_OK)