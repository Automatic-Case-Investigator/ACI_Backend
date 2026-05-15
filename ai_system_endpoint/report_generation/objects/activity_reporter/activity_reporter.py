from django.conf import settings
import requests
import traceback


class ActivityReporter:
    def generate_report(
        self,
        case_title: str,
        case_description: str,
        task_title: str,
        task_description: str,
        activity: str,
        report_template: str,
        additional_notes: str | None = None,
    ) -> dict:
        try:
            request_data = {
                "case_title": case_title,
                "case_description": case_description,
                "task_title": task_title,
                "task_description": task_description,
                "activity": activity,
                "report_template": report_template,
            }
            if additional_notes is not None and str(additional_notes).strip() != "":
                request_data["additional_notes"] = additional_notes

            response = requests.post(
                settings.AI_BACKEND_URL
                + "/report_generation_model/generate_activity_report/",
                headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
                data=request_data,
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
