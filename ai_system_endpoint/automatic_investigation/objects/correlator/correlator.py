from django.conf import settings
import requests

class Correlator:
    def query(self, event_data, title, description, activity, siem_type) -> dict:
        response = requests.post(
            settings.AI_BACKEND_URL + "/correlation_model/query/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "event": event_data,
                "case_title": title,
                "case_description": description,
                "activity": activity,
                "siem_type": siem_type
            },
        )
        return response.json()
