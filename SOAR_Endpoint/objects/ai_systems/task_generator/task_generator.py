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

    def extract_case_description(self, case_data):
        if str(type(self.soarwrapper)) == str(thehive_wrapper.TheHiveWrapper):
            return case_data["description"]

    def generate_task(self, case_data) -> dict:
        description = self.extract_case_description(case_data)

        if description is None:
            raise TypeError("Did not specify the SOAR platform")

        response = requests.post(
            settings.OLLAMA_URL,
            json={
                "model": "task_generation",
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a soc analyst. You received a case in the soar platform, including detailed information about an alert. The title section includes a brief description of the case, and the description section includes detailed information about the case. Based on the case information, list only the tasks you would suggest to create for investigating the incident. For each task, write only one sentence for title and description. Your answer should follow this format:Task # Title: <title> Description: <description>... Here is the decoded data of the case:",
                    },
                    {
                        "role": "user",
                        "content": f"{description}",
                    },
                ],
            },
        )
        answer_raw = response.json()["message"]["content"].replace("\r", "")
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
