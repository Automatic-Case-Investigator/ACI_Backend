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
        try:
            raw_response["id"] = raw_response["_id"]
            raw_response["createdBy"] = raw_response["_createdBy"]
            raw_response["createdAt"] = raw_response["_createdAt"]
            raw_response["type"] = raw_response["_type"]
            del raw_response["_id"]
            del raw_response["_createdBy"]
            del raw_response["_createdAt"]
            del raw_response["_type"]
        except KeyError:
            pass
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
        except requests.exceptions.ConnectionError as e:
            return {
                "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
            }

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def get_case(self, case_id):
        try:
            url = (
                f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/case/{case_id}"
            )
            response = requests.get(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
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

    def get_cases(self, org_id, search_str: str, page_size: int, page_number: int):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"
            query = {"query": [{"_name": "listCase"}]}
            if search_str is not None and len(search_str) > 0:
                query["query"].append(
                    {
                        "_name": "filter",
                        "_like": {"_field": "title", "_value": f"{search_str}"},
                    }
                )
            
            # Attempts to get the total number of cases
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Organisation": f"{org_id}",
                },
                json=query,
            )
            case_count = len(response.json())
            
            # Fetches the cases with pagination
            query["query"].append(
                {
                    "_name": "page",
                    "from": page_size * (page_number - 1),
                    "to": page_size * page_number,
                }
            )
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Organisation": f"{org_id}",
                },
                json=query,
            )

            output = []
            for case_data in response.json():
                formatted = self.format_response(case_data)
                output.append(formatted)
            return {"total_count": case_count, "cases": output}
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

            response = None
            if org_id is None:
                response = requests.get(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                )
            else:
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

            response = None
            if org_id is None:
                response = requests.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json={
                        "query": [
                            {"_name": "getCase", "idOrName": case_id},
                            {"_name": "tasks"},
                        ]
                    },
                )
            else:
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
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/case/{case_id}/task"
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
            return {"message": "Success"}
        except requests.exceptions.ConnectionError:
            return {
                "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
            }
