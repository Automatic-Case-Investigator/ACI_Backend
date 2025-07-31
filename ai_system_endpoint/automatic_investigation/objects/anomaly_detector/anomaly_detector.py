from django.conf import settings
import requests

class AnomalyDetector:
    def query(self, event_data, siem_type) -> dict:
        response = requests.post(
            settings.AI_BACKEND_URL + "/anomaly_detection_model/query/",
            headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
            data={
                "event_data": event_data,
                "siem_type": siem_type
            },
        )
        return response.json()
