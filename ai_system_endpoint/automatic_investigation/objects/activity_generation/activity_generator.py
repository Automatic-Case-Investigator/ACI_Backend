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


class ActivityGenerator:
    soarwrapper = None

    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper
        
    def extract_task_title(self, task_data):
        if str(type(self.soarwrapper)) == str(thehive_wrapper.TheHiveWrapper):
            return task_data["title"]

    def extract_task_description(self, task_data):
        if str(type(self.soarwrapper)) == str(thehive_wrapper.TheHiveWrapper):
            return task_data["description"]
        
    def generate_activity(self, case_title, task_data) -> dict:
        title = self.extract_task_title(task_data)
        description = self.extract_task_description(task_data)

        if title is None:
            raise TypeError("Title is not provided")
        
        if description is None:
            raise TypeError("Description is not provided")

        response = requests.post(
            settings.AI_BACKEND_URL + "/activity_generation_model/generate/",
            data={
                "case_title": case_title,
                "task_title": title,
                "task_description": description
            }
        )
        answer_raw = response.json()["result"]
        activities = answer_raw.split("\n")
        output = []
        
        for activity in activities:
            bulletpoint_search = re.search(" *[0-9]+. +", activity)
            if bulletpoint_search is not None:
                activity_string = re.sub(" *[0-9]+. +", "", activity)
                output.append(activity_string)
                
        return {"activities": output}
