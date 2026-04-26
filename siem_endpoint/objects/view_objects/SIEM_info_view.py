import hashlib
import json
import logging
from urllib.parse import quote

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import HttpResponse
from siem_endpoint import models

logger = logging.getLogger(__name__)


class SIEMInfoView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _parse_config_file_hashes(self, request):
        raw_hashes = request.data.get("config_file_hashes")
        if raw_hashes is None:
            return {}

        if isinstance(raw_hashes, dict):
            return raw_hashes

        if isinstance(raw_hashes, str):
            raw_hashes = raw_hashes.strip()
            if raw_hashes == "":
                return {}
            try:
                parsed_hashes = json.loads(raw_hashes)
            except json.JSONDecodeError:
                return None
            return parsed_hashes if isinstance(parsed_hashes, dict) else None

        return None

    def _serialize_config_files(self, siem_obj):
        config_files_data = []
        for config_obj in siem_obj.config_files.all():
            file_content = config_obj.content or b""
            config_files_data.append(
                {
                    "filename": config_obj.filename,
                    "hash_digest": hashlib.sha256(file_content).hexdigest(),
                }
            )
        return config_files_data

    def _vector_db_delete_filenames(self, filenames):
        if not filenames:
            return None

        try:
            response = requests.delete(
                settings.AI_BACKEND_URL + "/supporting_file/config_files/",
                headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
                json={"filenames": filenames},
                timeout=20,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to delete config files from vector db")
            return {"error": f"Failed to delete config files from vector db: {exc}"}

        if response.status_code >= 400:
            logger.error(
                "Vector db delete failed: status=%s body=%s",
                response.status_code,
                response.text,
            )
            return {
                "error": "Vector db delete failed",
                "status_code": response.status_code,
                "detail": response.text,
            }

        return None

    def _vector_db_upload_file(self, filename, content):
        files_payload = [("files", (filename, content, "application/octet-stream"))]
        target_url = settings.AI_BACKEND_URL + "/supporting_file/config_files/"
        if not settings.AI_BACKEND_URL:
            return {"error": "AI_BACKEND_URL is not configured"}

        try:
            response = requests.post(
                target_url,
                headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
                files=files_payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to upload config file to vector db: %s", filename)
            return {
                "error": f"Failed to upload config file to vector db: {filename}. {exc}"
            }

        if response.status_code >= 400:
            logger.error(
                "Vector db upload failed for %s: status=%s body=%s",
                filename,
                response.status_code,
                response.text,
            )
            return {
                "error": f"Vector db upload failed for {filename}",
                "status_code": response.status_code,
                "detail": response.text,
            }

        return None

    def _sync_config_files(self, siem_obj, config_files, client_hashes):
        existing_config_objs = {
            obj.filename: obj for obj in siem_obj.config_files.all()
        }
        uploaded_file_map = {
            uploaded_file.name: uploaded_file for uploaded_file in config_files
        }

        requested_filenames = set(client_hashes.keys()) | set(uploaded_file_map.keys())
        filenames_to_remove = []
        files_to_upsert = []

        # Files not present in the request should be removed
        for existing_filename in list(existing_config_objs.keys()):
            if existing_filename not in requested_filenames:
                filenames_to_remove.append(existing_filename)

        # Validate non-uploaded files against digests provided by client.
        for filename, client_digest in client_hashes.items():
            if filename in uploaded_file_map:
                continue

            existing_obj = existing_config_objs.get(filename)
            if existing_obj is None:
                return {"error": f"Missing uploaded file for new filename: {filename}"}

            existing_digest = hashlib.sha256(existing_obj.content or b"").hexdigest()
            if client_digest != existing_digest:
                return {
                    "error": f"Hash digest changed for {filename}, upload the updated file content."
                }

        # Decide which uploaded files require an upsert
        for filename, uploaded_file in uploaded_file_map.items():
            uploaded_content = uploaded_file.read()

            if b"\x00" in uploaded_content:
                return {"error": f"Config file {filename} must be plaintext UTF-8."}

            try:
                uploaded_content.decode("utf-8")
            except UnicodeDecodeError:
                return {"error": f"Config file {filename} must be plaintext UTF-8."}

            existing_obj = existing_config_objs.get(filename)
            existing_digest = (
                hashlib.sha256(existing_obj.content or b"").hexdigest()
                if existing_obj is not None
                else None
            )
            client_digest = client_hashes.get(filename)

            # Prefer client-provided digest for change detection; if absent, fallback to uploaded content digest
            if client_digest is None:
                client_digest = hashlib.sha256(uploaded_content).hexdigest()

            if existing_obj is None or existing_digest != client_digest:
                files_to_upsert.append((filename, uploaded_content))

        for filename in filenames_to_remove:
            existing_config_objs[filename].delete()

        # Deletes locally stored files
        for filename, uploaded_content in files_to_upsert:
            models.SIEMConfigFile.objects.update_or_create(
                siem=siem_obj,
                filename=filename,
                defaults={"content": uploaded_content},
            )

        # Deletes removed files and old versions of changed files.
        changed_existing_filenames = [
            filename
            for filename, _ in files_to_upsert
            if filename in existing_config_objs
        ]
        deletion_error = self._vector_db_delete_filenames(
            filenames_to_remove + changed_existing_filenames
        )
        if deletion_error is not None:
            return deletion_error

        # Updates new versions of changed files
        for filename, uploaded_content in files_to_upsert:
            upload_error = self._vector_db_upload_file(filename, uploaded_content)
            if upload_error is not None:
                return upload_error

        return None

    def get(self, request, *args, **kwargs):
        siem_objs = models.SIEMInfo.objects.all()
        output = {"message": []}

        for siem in siem_objs:
            output["message"].append(
                {
                    "id": siem.id,
                    "siem_type": siem.siem_type,
                    "use_api_key": siem.use_api_key,
                    "api_key": siem.api_key,
                    "username": siem.username,
                    "password": siem.password,
                    "protocol": siem.protocol,
                    "hostname": siem.hostname,
                    "base_dir": siem.base_dir,
                    "name": siem.name,
                    "config_files": self._serialize_config_files(siem),
                }
            )

        return Response(output, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        siem_id = request.data.get("siem_id")
        if siem_id is None:
            return Response(
                {"error": "Required field missing"}, status=status.HTTP_400_BAD_REQUEST
            )

        siem_obj = models.SIEMInfo.objects.filter(id=siem_id).first()
        if siem_obj is None:
            return Response(
                {"error": "SIEM not found"}, status=status.HTTP_404_NOT_FOUND
            )

        filenames = [config_obj.filename for config_obj in siem_obj.config_files.all()]
        siem_obj.delete()

        delete_error = self._vector_db_delete_filenames(filenames)
        if delete_error is not None:
            return Response(delete_error, status=status.HTTP_502_BAD_GATEWAY)

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
        config_files = request.FILES.getlist("config_files")
        config_file_hashes = self._parse_config_file_hashes(request)

        if config_file_hashes is None:
            return Response(
                {"error": "Invalid config_file_hashes format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if siem_id is None:
            # Creating new SIEMInfo object
            if siem_type is None:
                return Response(
                    {"error": "Required field missing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
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
                siem_obj = models.SIEMInfo(
                    siem_type=siem_type,
                    use_api_key=(
                        use_api_key
                        if isinstance(use_api_key, bool)
                        else str(use_api_key).lower() == "true"
                    ),
                    api_key=api_key,
                    username=username,
                    password=password,
                    protocol=protocol,
                    name=name,
                    hostname=hostname,
                    base_dir=base_dir,
                )
                siem_obj.save()
                sync_error = self._sync_config_files(
                    siem_obj, config_files, config_file_hashes
                )
                if sync_error is not None:
                    return Response(sync_error, status=status.HTTP_400_BAD_REQUEST)
                return Response({"message": "Success"}, status=status.HTTP_200_OK)
            except ValueError:
                return Response(
                    {"error": "Invalid SIEM type"}, status=status.HTTP_400_BAD_REQUEST
                )

        else:
            # Update a pre-existing SIEMInfo object
            try:
                siem_obj = models.SIEMInfo.objects.filter(id=siem_id).first()
                if siem_obj is None:
                    return Response(
                        {"error": "SIEM not found"}, status=status.HTTP_404_NOT_FOUND
                    )

                if siem_type is not None:
                    siem_obj.siem_type = siem_type
                if use_api_key is not None:
                    siem_obj.use_api_key = (
                        use_api_key
                        if isinstance(use_api_key, bool)
                        else str(use_api_key).lower() == "true"
                    )
                if api_key is not None:
                    siem_obj.api_key = api_key
                if username is not None:
                    siem_obj.username = username
                if password is not None:
                    siem_obj.password = password
                if protocol is not None:
                    siem_obj.protocol = protocol
                if name is not None:
                    siem_obj.name = name
                if hostname is not None:
                    siem_obj.hostname = hostname
                if base_dir is not None:
                    siem_obj.base_dir = base_dir

                siem_obj.save()
                sync_error = self._sync_config_files(
                    siem_obj, config_files, config_file_hashes
                )
                if sync_error is not None:
                    return Response(sync_error, status=status.HTTP_400_BAD_REQUEST)
                return Response({"message": "Success"}, status=status.HTTP_200_OK)
            except ValueError:
                return Response(
                    {"error": "Invalid SIEM type"}, status=status.HTTP_400_BAD_REQUEST
                )


class SIEMConfigFileDownloadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        siem_id = request.GET.get("siem_id")
        filename = request.GET.get("filename")

        if siem_id is None or filename is None:
            return Response(
                {"error": "Required field missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config_file = models.SIEMConfigFile.objects.filter(
            siem_id=siem_id,
            filename=filename,
        ).first()

        if config_file is None:
            return Response(
                {"error": "Config file not found"}, status=status.HTTP_404_NOT_FOUND
            )

        response = HttpResponse(
            config_file.content, content_type="text/plain; charset=utf-8"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{quote(config_file.filename)}"'
        )
        return response
