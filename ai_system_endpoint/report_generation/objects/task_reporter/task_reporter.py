from django.conf import settings
import requests
import traceback


class TaskReporter:
    def generate_report(
        self,
        case_title: str,
        case_description: str,
        task_title: str,
        task_description: str,
        activity_reports: list[str],
    ) -> dict:
        try:
            response = requests.post(
                settings.AI_BACKEND_URL + "/report_generation_model/generate_task_report/",
                headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
                data={
                    "case_title": case_title,
                    "case_description": case_description,
                    "task_title": task_title,
                    "task_description": task_description,
                    "activity_reports": activity_reports,
                },
                timeout=None,
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            traceback.format_exc()
            return {
                "error": "Unable to connect to the AI backend. Please contact the administrator for this problem."
            }
        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The AI backend returned an invalid response format."
            }
