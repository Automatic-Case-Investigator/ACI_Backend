from django.conf import settings
import importlib.util
import requests
import json

module_spec = importlib.util.spec_from_file_location(
    "soar_endpoint.objects.soar_wrapper.thehive_wrapper",
    "soar_endpoint/objects/soar_wrapper/thehive_wrapper.py",
)
wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(wrapper)


class ActivityCompletionChecker:
    soarwrapper = None

    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper

    def extract_title(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["title"]

    def extract_description(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["description"]

    def check_completeness(self, case_title: str, case_description: str, task_data: dict[str, str], activity: str, queries: list[str], query_summaries: list[str], web_search: bool = False) -> dict:
        title = self.extract_title(task_data)
        description = self.extract_description(task_data)

        if title is None:
            raise TypeError("Title is not provided")

        if description is None:
            raise TypeError("Description is not provided")

        response = requests.post(
            settings.AI_BACKEND_URL + "/completion_check_model/activity_completion_check/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "case_title": case_title,
                "case_description": case_description,
                "task_title": title,
                "task_description": description,
                "activity": activity,
                "queries": queries,
                "query_summaries": query_summaries,
                "web_search": int(web_search)
            },
        )
        return response.json()
