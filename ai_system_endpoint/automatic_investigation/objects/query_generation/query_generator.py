from django.conf import settings
import importlib.util
import requests

module_spec = importlib.util.spec_from_file_location(
    "soar_endpoint.objects.soar_wrapper.thehive_wrapper",
    "soar_endpoint/objects/soar_wrapper/thehive_wrapper.py",
)
wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(wrapper)


class QueryGenerator:
    soarwrapper = None

    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper

    def extract_title(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["title"]

    def extract_description(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["description"]

    def generate_query_from_prompt(self, prompt: str) -> dict:
        response = requests.post(
            settings.AI_BACKEND_URL + "/query_generation_model/generate/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "prompt": prompt,
                "siem": "wazuh",  # TODO: SIEM wrapper should be implemented and replace this hardcoded value
            },
        )
        return response.json()

    def generate_query_from_case(self, case_title, case_description, task_data, activity) -> dict:
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
        return response.json()
