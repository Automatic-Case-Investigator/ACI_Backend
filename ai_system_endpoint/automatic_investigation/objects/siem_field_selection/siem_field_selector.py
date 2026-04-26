from django.conf import settings
import requests


class SIEMFieldSelector:
	def select(
		self,
		case_title: str,
		case_description: str,
		task_title: str,
		task_description: str,
		activity: str,
		available_fields: list[str] = None,
	):
		response = requests.post(
			settings.AI_BACKEND_URL + "/siem_field_selector_model/select_siem_fields/",
			headers={"Authorization": f"Bearer {settings.AI_BACKEND_API_KEY}"},
			data={
				"case_title": case_title,
				"case_description": case_description,
				"task_title": task_title,
				"task_description": task_description,
				"activity": activity,
				"available_siem_fields": available_fields or [],
			},
		)
		return response.json().get("result", [])
