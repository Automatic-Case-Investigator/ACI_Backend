from django.conf import settings
import importlib.util
import requests
import re

module_spec = importlib.util.spec_from_file_location(
    "SOAR_Endpoint.objects.soar_wrapper.thehive_wrapper",
    "SOAR_Endpoint/objects/soar_wrapper/thehive_wrapper.py",
)
thehive_wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(thehive_wrapper)


class TaskGenerator:
    soarwrapper = None

    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper
        
    def extract_case_title(self, case_data):
        if str(type(self.soarwrapper)) == str(thehive_wrapper.TheHiveWrapper):
            return case_data["title"]

    def extract_case_description(self, case_data):
        if str(type(self.soarwrapper)) == str(thehive_wrapper.TheHiveWrapper):
            return case_data["description"]

    def generate_task(self, case_data) -> dict:
        title = self.extract_case_title(case_data)
        description = self.extract_case_description(case_data)

        if description is None:
            raise TypeError("Did not specify the SOAR platform")

        response = requests.post(
            settings.AI_BACKEND_URL + "/task_generation_model/generate/",
            data={
                "case_title": title,
                "case_description": description
            }
        )
        answer_raw = response.json()["result"]
        print(answer_raw)
        tasks = answer_raw.split("\n\n")
        seen_tags = []

        for task in tasks:
            task_formatted = {"Tag": "", "Title": "", "Description": ""}
            task_tag_search = re.search("Task", task)
            task_title_search = re.search("Title: ", task)
            task_description_search = re.search("Description: ", task)
            if task_tag_search and task_title_search and task_description_search:
                tag = task[task_tag_search.start() : task_title_search.start()].split("\n")[0]
                
                if tag in seen_tags:
                    continue
                
                seen_tags.append(tag)
                task_formatted["Tag"] = tag
                
                task_formatted["Title"] = task[
                    task_title_search.start() + 7 : task_description_search.start()
                ].split("\n")[0]
                
                task_formatted["Description"] = task[task_description_search.start() + 13 :].split("\n")[0]
                result = self.soarwrapper.create_task_in_case(
                    case_id=case_data["id"], task_data=task_formatted
                )
                if "error" in result.keys():
                    return result

        return {"message": "Success"}
