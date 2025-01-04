from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from SOAR_Endpoint import models

class SOARInfoView(APIView):
    def get(self, request, *args, **kwargs):
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
        
        return Response(output, status=status.HTTP_200_OK)
    
    def delete(self, request, *args, **kwargs):
        soar_id = request.data.get("soar_id")
        if soar_id is None:
            return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)
        
        models.SOARInfo.objects.filter(id=soar_id).delete()
        return Response({"message": "Success"}, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        """Set SOAR info in the database

        parameters:
            soar_id (optional): id of the SOAR platform
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
        soar_id = request.data.get("soar_id")
        soar_type = request.data.get("soar_type")
        api_key = request.data.get("api_key")
        protocol = request.data.get("protocol")
        name = request.data.get("name")
        hostname = request.data.get("hostname")
        base_dir = request.data.get("base_dir")
        
        if soar_id is None:
            # Creating new SOARInfo object
            if soar_type is None:
                return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)
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
                return Response({"message": "Success"}, status=status.HTTP_200_OK)
            except ValueError:
                return Response({"error": "Invalid SOAR type"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Update a pre-existing SOARInfo object
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
                return Response({"message": "Success"}, status=status.HTTP_200_OK)
            except ValueError:
                return Response({"error": "Invalid SOAR type"}, status=status.HTTP_400_BAD_REQUEST)