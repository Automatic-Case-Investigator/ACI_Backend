from .soar_wrapper import SOARWrapper
import requests


class TheHiveWrapper(SOARWrapper):
    def __init__(self, protocol, hostname, base_dir, api_key):
        SOARWrapper.__init__(self, protocol, hostname, base_dir, api_key)

    def get_case(self, case_id):
        url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/case/{case_id}"
        response = requests.get(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        return response.json()

    def create_task_in_case(self, case_id, task_data):
        url = (
            f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/case/{case_id}/task"
        )
        requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            json={
                "title": task_data["Title"],
                "description": task_data["Description"],
                "status": "Waiting",
            },
        )
