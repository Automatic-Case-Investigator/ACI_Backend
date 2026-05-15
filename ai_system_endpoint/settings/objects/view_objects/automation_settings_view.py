from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ai_system_endpoint.settings.models import AutomationSettings


class AutomationSettingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    VALID_UNITS = (
        "hours",
        "days",
        "weeks",
        "months",
        "years",
    )

    DEFAULT_SETTINGS = {
        "enableWebSearch": {
            "task_generation": False,
            "activity_generation": False,
            "siem_investigation": False,
        },
        "earliestMagnitude": 1,
        "earliestUnit": "years",
        "vicinityMagnitude": 1,
        "vicinityUnit": "hours",
        "maxIterations": 3,
        "maxQueriesPerIteration": 5,
        "additionalNotes": "",
    }

    def _serialize_updated_at(self, settings_obj: AutomationSettings) -> str:
        return settings_obj.updated_at.isoformat().replace("+00:00", "Z")

    def _normalize_settings(self, raw_settings) -> dict:
        normalized = {
            "enableWebSearch": {
                "task_generation": False,
                "activity_generation": False,
                "siem_investigation": False,
            },
            "earliestMagnitude": 1,
            "earliestUnit": "years",
            "vicinityMagnitude": 1,
            "vicinityUnit": "hours",
            "maxIterations": 3,
            "maxQueriesPerIteration": 5,
            "additionalNotes": "",
        }

        if not isinstance(raw_settings, dict):
            return normalized

        web_search = raw_settings.get("enableWebSearch")
        if isinstance(web_search, dict):
            for key in normalized["enableWebSearch"]:
                value = web_search.get(key)
                if isinstance(value, bool):
                    normalized["enableWebSearch"][key] = value

        earliest_magnitude = raw_settings.get("earliestMagnitude")
        if isinstance(earliest_magnitude, int) and earliest_magnitude > 0:
            normalized["earliestMagnitude"] = earliest_magnitude

        earliest_unit = raw_settings.get("earliestUnit")
        if isinstance(earliest_unit, str) and earliest_unit in self.VALID_UNITS:
            normalized["earliestUnit"] = earliest_unit

        vicinity_magnitude = raw_settings.get("vicinityMagnitude")
        if isinstance(vicinity_magnitude, int) and vicinity_magnitude > 0:
            normalized["vicinityMagnitude"] = vicinity_magnitude

        vicinity_unit = raw_settings.get("vicinityUnit")
        if isinstance(vicinity_unit, str) and vicinity_unit in self.VALID_UNITS:
            normalized["vicinityUnit"] = vicinity_unit

        max_iterations = raw_settings.get("maxIterations")
        if isinstance(max_iterations, int) and max_iterations > 0:
            normalized["maxIterations"] = min(max_iterations, 20)

        max_queries_per_iteration = raw_settings.get("maxQueriesPerIteration")
        if isinstance(max_queries_per_iteration, int) and max_queries_per_iteration > 0:
            normalized["maxQueriesPerIteration"] = min(max_queries_per_iteration, 20)

        additional_notes = raw_settings.get("additionalNotes")
        if isinstance(additional_notes, str):
            normalized["additionalNotes"] = additional_notes

        return normalized

    def _validate_payload(self, data: dict) -> tuple[bool, dict]:
        required_fields = ("soar_id", "org_id", "case_id", "automation_settings")
        missing_fields = [field for field in required_fields if field not in data]
        empty_fields = [
            field
            for field in ("soar_id", "org_id", "case_id")
            if field in data and str(data.get(field)).strip() == ""
        ]

        if missing_fields or empty_fields:
            return False, {
                "error": "Invalid parameters",
                "missing_fields": missing_fields,
                "empty_fields": empty_fields,
            }

        automation_settings = data.get("automation_settings")
        if not isinstance(automation_settings, dict):
            return False, {"error": 'Parameter "automation_settings" must be an object'}

        if "enableWebSearch" not in automation_settings:
            return False, {"error": 'Parameter "enableWebSearch" is required'}

        web_search = automation_settings.get("enableWebSearch")
        if not isinstance(web_search, dict):
            return False, {"error": 'Parameter "enableWebSearch" must be an object'}

        required_web_search_keys = (
            "task_generation",
            "activity_generation",
            "siem_investigation",
        )
        for key in required_web_search_keys:
            if key not in web_search:
                return False, {"error": f'Parameter "enableWebSearch.{key}" is required'}
            if not isinstance(web_search.get(key), bool):
                return False, {
                    "error": f'Parameter "enableWebSearch.{key}" must be a boolean'
                }

        required_int_fields = (
            "earliestMagnitude",
            "vicinityMagnitude",
            "maxIterations",
            "maxQueriesPerIteration",
        )
        for field in required_int_fields:
            value = automation_settings.get(field)
            if isinstance(value, bool) or not isinstance(value, int):
                return False, {"error": f'Parameter "{field}" must be an integer'}
            if value <= 0:
                return False, {"error": f'Parameter "{field}" must be greater than 0'}

        for field in ("earliestUnit", "vicinityUnit"):
            value = automation_settings.get(field)
            if not isinstance(value, str):
                return False, {"error": f'Parameter "{field}" must be a string'}
            if value not in self.VALID_UNITS:
                return False, {"error": f'Parameter "{field}" is not a valid unit'}

        additional_notes = automation_settings.get("additionalNotes")
        if additional_notes is None:
            automation_settings["additionalNotes"] = ""
        elif not isinstance(additional_notes, str):
            return False, {"error": 'Parameter "additionalNotes" must be a string'}

        return True, {}

    def get(self, request, *args, **kwargs):
        soar_id = request.query_params.get("soar_id")
        org_id = request.query_params.get("org_id")
        case_id = request.query_params.get("case_id")

        if not soar_id or not org_id or not case_id:
            return Response(
                {
                    "error": "Invalid parameters",
                    "missing_fields": [
                        field
                        for field, value in (
                            ("soar_id", soar_id),
                            ("org_id", org_id),
                            ("case_id", case_id),
                        )
                        if not value
                    ],
                    "empty_fields": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        settings_obj, _ = AutomationSettings.objects.get_or_create(
            user=request.user,
            soar_id=soar_id,
            org_id=org_id,
            case_id=case_id,
            defaults={"settings": self.DEFAULT_SETTINGS},
        )

        serialized_settings = self._normalize_settings(settings_obj.settings)
        if settings_obj.settings != serialized_settings:
            settings_obj.settings = serialized_settings
            settings_obj.save(update_fields=["settings", "updated_at"])

        return Response(
            {
                "settings": serialized_settings,
                "updated_at": self._serialize_updated_at(settings_obj),
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):
        data = request.data

        is_valid, error_payload = self._validate_payload(data)
        if not is_valid:
            return Response(error_payload, status=status.HTTP_400_BAD_REQUEST)

        settings_obj, _ = AutomationSettings.objects.get_or_create(
            user=request.user,
            soar_id=data.get("soar_id"),
            org_id=data.get("org_id"),
            case_id=data.get("case_id"),
            defaults={"settings": self.DEFAULT_SETTINGS},
        )

        normalized_settings = self._normalize_settings(data.get("automation_settings"))
        settings_obj.settings = normalized_settings
        settings_obj.save(update_fields=["settings", "updated_at"])

        return Response(
            {
                "message": "Settings saved successfully",
                "settings": normalized_settings,
                "updated_at": self._serialize_updated_at(settings_obj),
            },
            status=status.HTTP_200_OK,
        )
