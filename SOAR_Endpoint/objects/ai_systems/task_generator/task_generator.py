from django.conf import settings
import importlib.util
import requests
import re

module_spec = importlib.util.spec_from_file_location("SOAR_Endpoint.objects.soar_wrapper.thehive_wrapper", "SOAR_Endpoint/objects/soar_wrapper/thehive_wrapper.py")
thehive_wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(thehive_wrapper)

class TaskGenerator:
    soarwrapper = None
    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper
        pass
    
    def extract_case_description(self, case_data):
        if str(type(self.soarwrapper)) == str(thehive_wrapper.TheHiveWrapper):
            return case_data["description"]

    def generate_task(self, case_data):
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
                        "content": "You are a soc analyst. You received a case in the soar platform, including detailed information about an alert. Based on the case information, list only the tasks you would suggest to create. For each task, write only one sentence for title and description. Your answer should follow this format:Task # Title: <title> Description: <description>... Here is the decoded data of the case:",
                    },
                    {
                        "role": "user",
                        "content": f"{description}",
                    },
                ],
            },
        )
        answer_raw = response.json()["message"]["content"]
        tasks = answer_raw.split("\n\n")
        
        for task in tasks:
            print(task)
            task_formatted = {
                "Tag": "",
                "Title": "",
                "Description": ""
            }
            task_tag_search = re.search("Task",task)
            task_title_search = re.search("Title: ",task)
            task_description_search = re.search("Description: ",task)
            task_formatted["Tag"] = task[task_tag_search.start():task_title_search.start()]
            task_formatted["Title"] = task[task_title_search.start() + 7:task_description_search.start()]
            task_formatted["Description"] = task[task_description_search.start() + 13:]
            self.soarwrapper.create_task_in_case(case_id=case_data["_id"], task_data=task_formatted)