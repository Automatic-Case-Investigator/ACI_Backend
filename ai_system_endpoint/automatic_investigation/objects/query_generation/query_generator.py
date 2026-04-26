from django.conf import settings
import importlib.util
import requests
from siem_endpoint import models as siem_models

module_spec = importlib.util.spec_from_file_location(
    "soar_endpoint.objects.soar_wrapper.thehive_wrapper",
    "soar_endpoint/objects/soar_wrapper/thehive_wrapper.py",
)
wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(wrapper)


class QueryGenerator:
    soarwrapper = None
    siem_id = None

    SIEM_TYPE_TO_BACKEND_NAME = {
        "WZ": "wazuh",
    }

    BACKEND_NAME_TO_SIEM_TYPE = {
        value: key for key, value in SIEM_TYPE_TO_BACKEND_NAME.items()
    }

    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper

    def set_siem_id(self, siem_id):
        self.siem_id = siem_id

    def extract_title(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["title"]

    def extract_description(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["description"]

    def _get_current_siem_backend_name(self) -> str:
        if self.siem_id is not None:
            siem_obj = siem_models.SIEMInfo.objects.filter(id=self.siem_id).first()
            if siem_obj is not None:
                return self.SIEM_TYPE_TO_BACKEND_NAME.get(siem_obj.siem_type, "wazuh")

        return "wazuh"

    def _config_file_exists(self, siem_backend_name: str) -> bool:
        if self.siem_id is not None:
            return siem_models.SIEMConfigFile.objects.filter(
                siem_id=self.siem_id
            ).exists()

        siem_type = self.BACKEND_NAME_TO_SIEM_TYPE.get(siem_backend_name)
        if siem_type is None:
            return False

        return siem_models.SIEMConfigFile.objects.filter(
            siem__siem_type=siem_type
        ).exists()

    def fix_queries(self, input_str: str) -> dict:
        response = requests.post(
            settings.AI_BACKEND_URL + "/query_generation_model/fix_queries/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "input_str": input_str,
                "siem": "wazuh",  # TODO: SIEM wrapper should be implemented and replace this hardcoded value
            },
        )
        return response.json()

    def generate_query_from_prompt(self, prompt: str) -> dict:
        siem_backend_name = self._get_current_siem_backend_name()
        search_config_files = self._config_file_exists(siem_backend_name)

        response = requests.post(
            settings.AI_BACKEND_URL + "/query_generation_model/generate/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "prompt": prompt,
                "siem": siem_backend_name,
                "search_config_files": search_config_files,
            },
        )
        return response.json()

    def generate_query_from_case(
        self,
        case_title: str,
        case_description: str,
        task_data: dict,
        activity: str,
        field_map: dict,
        prev_activity_critique: str,
        additional_notes: str,
        earliest_unit: str,
        earliest_magnitude: int,
        vicinity_unit: str,
        vicinity_magnitude: int,
        max_queries_per_iteration: int,
    ) -> dict:
        if case_title is None:
            raise TypeError("Case title is not provided")

        if case_description is None:
            raise TypeError("Case description is not provided")

        if task_data is None:
            raise TypeError("Task data is not provided")

        task_title = self.extract_title(task_data)
        task_description = self.extract_description(task_data)

        if task_title is None:
            raise TypeError("Title is not provided")

        if task_description is None:
            raise TypeError("Description is not provided")

        if activity is None:
            raise TypeError("Activity data is not provided")

        siem_backend_name = self._get_current_siem_backend_name()
        search_config_files = self._config_file_exists(siem_backend_name)

        request_data = {
            "case_title": case_title,
            "case_description": case_description,
            "task_title": task_title,
            "task_description": task_description,
            "activity": activity,
            "earliest_unit": earliest_unit,
            "earliest_magnitude": earliest_magnitude,
            "vicinity_unit": vicinity_unit,
            "vicinity_magnitude": vicinity_magnitude,
            "siem": siem_backend_name,
            "search_config_files": search_config_files,
        }

        if additional_notes is not None and additional_notes.strip() != "":
            request_data["additional_notes"] = additional_notes

        if prev_activity_critique is not None and prev_activity_critique.strip() != "":
            request_data["prev_activity_critique"] = prev_activity_critique

        if max_queries_per_iteration is not None:
            request_data["max_queries_per_iteration"] = max_queries_per_iteration

        if field_map is not None:
            field_data = ""
            for field, field_info in field_map.items():
                field_data += f"{field}: {field_info}\n"

            request_data["fields"] = field_data

        response = requests.post(
            settings.AI_BACKEND_URL + "/query_generation_model/generate/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data=request_data,
            timeout=None,
        )
        result = response.json()
        if "result" in result:
            normalized_lines = []
            for line in result["result"].splitlines():
                stripped = line.lstrip()
                # Normalise common bullet styles to hyphen
                if stripped and not stripped.startswith("-"):
                    import re as _re

                    if _re.match(r"^(\*|\•|\d+[\.\)])\s", stripped):
                        stripped = _re.sub(r"^(\*|\•|\d+[\.\)])\s+", "- ", stripped)
                normalized_lines.append(stripped if stripped else line)
            result["result"] = "\n".join(normalized_lines)
        return result
