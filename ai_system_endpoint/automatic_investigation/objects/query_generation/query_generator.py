from django.conf import settings
import importlib.util
import requests
import re

module_spec = importlib.util.spec_from_file_location(
    "soar_endpoint.objects.soar_wrapper.thehive_wrapper",
    "soar_endpoint/objects/soar_wrapper/thehive_wrapper.py",
)
thehive_wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(thehive_wrapper)


class QueryGenerator:
    soarwrapper = None

    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper

    def extract_title(self, task_data):
        if str(type(self.soarwrapper)) == str(thehive_wrapper.TheHiveWrapper):
            return task_data["title"]

    def extract_description(self, task_data):
        if str(type(self.soarwrapper)) == str(thehive_wrapper.TheHiveWrapper):
            return task_data["description"]

    def generate_query(self, case_title, case_description, task_data, activity) -> dict:
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

        response = requests.post(
            settings.AI_BACKEND_URL + "/query_generation_model/generate/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "case_title": case_title,
                "case_description": case_description,
                "task_title": task_title,
                "task_description": task_description,
                "activity": activity,
                "siem": "wazuh",  # TODO: SIEM wrapper should be implemented and replace this hardcoded value
            },
        )
        answer_raw = response.json()["result"]
        return {"result": answer_raw}
