from django.conf import settings
import importlib.util
import aiohttp
import asyncio

module_spec = importlib.util.spec_from_file_location(
    "soar_endpoint.objects.soar_wrapper.thehive_wrapper",
    "soar_endpoint/objects/soar_wrapper/thehive_wrapper.py",
)
wrapper = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(wrapper)


class RelevencyFilter:
    soarwrapper = None

    def set_soarwrapper(self, soarwrapper):
        self.soarwrapper = soarwrapper

    def extract_title(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["title"]

    def extract_description(self, task_data):
        if str(type(self.soarwrapper)) == str(wrapper.TheHiveWrapper):
            return task_data["description"]

    async def check_relevency(
        self,
        case_title: str,
        case_description: str,
        task_data: dict[str, str],
        activity: str,
        additional_notes: str,
        query: str,
        event: str,
        web_search: bool = False,
    ) -> dict:
        title = self.extract_title(task_data)
        description = self.extract_description(task_data)

        if title is None:
            raise TypeError("Title is not provided")

        if description is None:
            raise TypeError("Description is not provided")

        request_data = {
            "case_title": case_title,
            "case_description": case_description,
            "task_title": title,
            "task_description": description,
            "activity": activity,
            "query": query,
            "event": event,
            "web_search": int(web_search),
        }

        if additional_notes is not None and additional_notes.strip() != "":
            request_data["additional_notes"] = additional_notes

        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.AI_BACKEND_URL + "/relevency_filter_model/generate/",
                headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
                data=request_data,
            ) as response:
                return await response.json()
