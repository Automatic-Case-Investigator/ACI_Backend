from .soar_wrapper import SOARWrapper
import requests


class TheHiveWrapper(SOARWrapper):
    def __init__(self, protocol, name, hostname, base_dir, api_key):
        SOARWrapper.__init__(
            self,
            protocol=protocol,
            name=name,
            hostname=hostname,
            base_dir=base_dir,
            api_key=api_key,
        )

    def get_organizations(self):
        url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"
        try:
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={"query": [{"_name": "listOrganisation"}]},
            )
            
            return response.json()
        except requests.exceptions.ConnectionError:
            return {"error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."}

        except requests.exceptions.JSONDecodeError:
            return {"error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."}

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
