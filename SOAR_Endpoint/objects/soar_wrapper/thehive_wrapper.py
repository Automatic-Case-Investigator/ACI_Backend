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

    def format_response(self, raw_response):
        raw_response["id"] = raw_response["_id"]
        raw_response["createdBy"] = raw_response["_createdBy"]
        raw_response["createdAt"] = raw_response["_createdAt"]
        raw_response["type"] = raw_response["_type"]
        del raw_response["_id"]
        del raw_response["_createdBy"]
        del raw_response["_createdAt"]
        del raw_response["_type"]
        return raw_response

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

            organizations = response.json()
            output = []
            for org in organizations:
                formatted = self.format_response(org)
                output.append(formatted)

            return {"organizations": output}
        except requests.exceptions.ConnectionError:
            return {
                "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
            }

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def get_case(self, case_id):
        url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/case/{case_id}"
        response = requests.get(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        return self.format_response(response.json())

    def get_cases(self, org_id):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Organisation": f"{org_id}",
                },
                json={"query": [{"_name": "listCase"}]},
            )

            output = []
            for case_data in response.json():
                formatted = self.format_response(case_data)
                output.append(formatted)
            return {"cases": output}
        except requests.exceptions.ConnectionError:
            return {
                "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
            }

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def get_task(self, org_id, task_id):
        try:
            url = (
                f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/task/{task_id}"
            )
            response = requests.get(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Organisation": f"{org_id}",
                },
            )

            return self.format_response(response.json())
        except requests.exceptions.ConnectionError:
            return {
                "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
            }

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def delete_task(self, task_id):
        try:
            url = (
                f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/task/{task_id}"
            )
            requests.delete(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            return {"message": "Success"}
        except requests.exceptions.ConnectionError:
            return {
                "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
            }

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def get_tasks(self, org_id, case_id):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Organisation": f"{org_id}",
                },
                json={
                    "query": [
                        {"_name": "getCase", "idOrName": case_id},
                        {"_name": "tasks"},
                    ]
                },
            )

            output = []
            for task in response.json():
                formatted = self.format_response(task)
                output.append(formatted)

            return {"tasks": output}
        except requests.exceptions.ConnectionError:
            return {
                "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
            }

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def get_task_logs(self, task_id):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "query": [
                        {"_name": "listLog", "idOrName": task_id},
                    ]
                },
            )

            output = []
            for task in response.json():
                formatted = self.format_response(task)
                output.append(formatted)

            return {"task_logs": output}
        except requests.exceptions.ConnectionError:
            return {
                "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
            }

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

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
                "group": "Automatic Case Investigator",
            },
        )
