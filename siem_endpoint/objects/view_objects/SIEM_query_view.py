from siem_endpoint.objects.siem_wrapper.siem_wrapper_builder import SIEMWrapperBuilder
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from siem_endpoint import models

class SIEMQueryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Query the SIEM platform with the provided query string.

        parameters:
            siem_id (optional): id of the SIEM platform
            query: SIEM query string

        Args:
            request (_type_): django request

        Returns:
            JsonResponse: Json response
        """
        siem_id = request.data.get("siem_id")
        query = request.data.get("query")

        if not all([siem_id, query]):
            return Response({"error": "Required fields missing"}, status=status.HTTP_400_BAD_REQUEST)
        
        siem_obj = models.SIEMInfo.objects.filter(id=siem_id).first()
        if siem_obj is None:
            return Response(
                {"error": "Target SIEM id not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        siem_wrapper_builder = SIEMWrapperBuilder()
        siem_wrapper = None
        try:
            siem_wrapper = siem_wrapper_builder.build_from_model_object(siem_info_obj=siem_obj)
        except TypeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response = siem_wrapper.query(query, output_full=True)
        if "error" in response.keys():
            if response["error"] == siem_wrapper.unable_to_connect_message["error"]:
                return Response(response, status=status.HTTP_502_BAD_GATEWAY)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
    

        return Response({"message": "success", "result": response}, status=status.HTTP_200_OK)
    
    