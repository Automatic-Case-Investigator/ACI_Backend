from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from siem_endpoint import models

class SIEMInfoView(APIView):
    def get(self, request, *args, **kwargs):
        siem_objs = models.SIEMInfo.objects.all()
        output = {"message": []}
        
        for siem in siem_objs:
            output["message"].append({
                "id": siem.id,
                "siem_type" : siem.siem_type,
                "use_api_key": siem.use_api_key,
                "api_key": siem.api_key,
                "username": siem.username,
                "password": siem.password,
                "protocol": siem.protocol,
                "hostname": siem.hostname,
                "base_dir": siem.base_dir,
                "name": siem.name
            })
        
        return Response(output, status=status.HTTP_200_OK)
    
    def delete(self, request, *args, **kwargs):
        siem_id = request.data.get("siem_id")
        if siem_id is None:
            return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)
        
        models.SIEMInfo.objects.filter(id=siem_id).delete()
        return Response({"message": "Success"}, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        """Set SIEM info in the database

        parameters:
            siem_id (optional): id of the SIEM platform
            siem_type: SIEM type (Eg. TH for The Hive)
            use_api_key: whether to use api key for authentication
            api_key: SIEM api key
            username: SIEM username
            password: SIEM password
            protocol: SIEM protocol (Eg. http: or https:)
            hostname: SIEM host name (host and port)
            base_dir: SIEM url base directory

        Args:
            request (_type_): django request

        Returns:
            JsonResponse: Json response
        """
        siem_id = request.data.get("siem_id")
        siem_type = request.data.get("siem_type")
        use_api_key = request.data.get("use_api_key")
        api_key = request.data.get("api_key")
        username = request.data.get("username")
        password = request.data.get("password")
        protocol = request.data.get("protocol")
        name = request.data.get("name")
        hostname = request.data.get("hostname")
        base_dir = request.data.get("base_dir")
        
        if siem_id is None:
            # Creating new SIEMInfo object
            if siem_type is None:
                return Response({"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST)
            if use_api_key is None:
                use_api_key = ""
            if api_key is None:
                api_key = ""
            if username is None:
                username = ""
            if password is None:
                password = ""
            if protocol is None:
                protocol = ""
            if hostname is None:
                hostname = ""
            if base_dir is None:
                base_dir = ""

            try:
                models.SIEMInfo(
                    siem_type=siem_type,
                    use_api_key=use_api_key == "true",
                    api_key=api_key,
                    username=username,
                    password=password,
                    protocol=protocol,
                    name=name,
                    hostname=hostname,
                    base_dir=base_dir,
                ).save()
                return Response({"message": "Success"}, status=status.HTTP_200_OK)
            except ValueError:
                return Response({"error": "Invalid SIEM type"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Update a pre-existing SIEMInfo object
            try:
                if siem_type is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(siem_type=siem_type)
                if use_api_key is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(use_api_key=use_api_key == "true")
                if api_key is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(api_key=api_key)
                if username is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(username=username)
                if password is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(password=password)
                if protocol is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(protocol=protocol)
                if name is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(name=name)
                if hostname is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(hostname=hostname)
                if base_dir is not None:
                    models.SIEMInfo.objects.filter(id=siem_id).update(base_dir=base_dir)
                return Response({"message": "Success"}, status=status.HTTP_200_OK)
            except ValueError:
                return Response({"error": "Invalid SIEM type"}, status=status.HTTP_400_BAD_REQUEST)