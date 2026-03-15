from ai_system_endpoint.automatic_investigation.objects.query_generation.query_generator import QueryGenerator
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
import requests

class QueryGenerationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        prompt = request.POST.get("prompt")
        
        try:
            # Create and run query generator
            query_generator = QueryGenerator()
            response = query_generator.generate_query_from_prompt(prompt=prompt)
            if "result" in response:
                return Response({ "query": response["result"] }, status=status.HTTP_200_OK)
            
        except requests.exceptions.ConnectionError:
            return Response(
                {
                    "error": "Unable to connect to the AI backend. Please contact the administrator."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
