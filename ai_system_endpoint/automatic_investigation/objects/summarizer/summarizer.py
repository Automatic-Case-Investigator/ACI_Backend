from django.conf import settings
import importlib.util
import requests

module_spec = importlib.util.spec_from_file_location(
    "soar_endpoint.objects.soar_wrapper.thehive_wrapper",
    "soar_endpoint/objects/soar_wrapper/thehive_wrapper.py",
)
wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(wrapper)


class QuerySummarizer:
    def summarize(self, query: str, events: str) -> dict:
        if len(events) == 0:
            events = "The query returned no events."

        response = requests.post(
            settings.AI_BACKEND_URL + "/summary_model/generate_query_summary/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "query": query,
                "events": events,
            },
        )
        return response.json()
    
class ActivitySummarizer:
    soarwrapper = None

    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper

    def extract_title(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["title"]

    def extract_description(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["description"]
        
    def summarize(self, case_title: str, case_description: str, task_data: dict[str, str], activity: str, queries: list[str], query_summaries: list[str], web_search: bool = False) -> dict:
        task_title = self.extract_title(task_data)
        task_description = self.extract_description(task_data)
        
        response = requests.post(
            settings.AI_BACKEND_URL + "/summary_model/generate_activity_summary/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "case_title": case_title,
                "case_description": case_description,
                "task_title": task_title,
                "task_description": task_description,
                "activity": activity,
                "queries": queries,
                "query_summaries": query_summaries,
                "web_search": int(web_search)
            },
        )
        return response.json()
