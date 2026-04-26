from .soar_wrapper import SOARWrapper
import requests


class TheHiveWrapper(SOARWrapper):
    unable_to_connect_message = {
        "error": "Unable to connect to the SOAR platform. Please make sure you have the correct connection settings."
    }
    success_message = {"message": "Success"}

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
            return TheHiveWrapper.unable_to_connect_message

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
            return TheHiveWrapper.unable_to_connect_message

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def get_cases(
        self,
        org_id,
        search_str: str,
        page_size: int,
        time_sort_type: int,
        page_number: int,
    ):
        query_update_funcs = {
            0: lambda query: query["query"].append(
                {"_name": "sort", "_fields": [{"_createdAt": "desc"}]}
            )
            or query,
            1: lambda query: query["query"].append(
                {"_name": "sort", "_fields": [{"_createdAt": "asc"}]}
            )
            or query,
        }
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"
            query = {"query": [{"_name": "listCase"}]}
            if time_sort_type is not None:
                query = query_update_funcs[time_sort_type](query)

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

            if page_number is not None:
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
            return TheHiveWrapper.unable_to_connect_message

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def get_observable(self, org_id, observable_id):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"

            query = {"query": [{"_name": "getObservable", "idOrName": observable_id}]}

            response = None
            if org_id is None:
                response = requests.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json=query,
                )
            else:
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
            for task in response.json():
                formatted = self.format_response(task)
                output.append(formatted)

            return {"observable": output}
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def get_observables(self, org_id, case_id):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"

            query = {
                "query": [
                    {"_name": "getCase", "idOrName": case_id},
                    {"_name": "observables"},
                ]
            }

            response = None
            if org_id is None:
                response = requests.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json=query,
                )
            else:
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
            for task in response.json():
                formatted = self.format_response(task)
                output.append(formatted)

            return {"observables": output}
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def delete_observable(self, observable_id):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/observable/{observable_id}"

            requests.delete(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

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
            return TheHiveWrapper.unable_to_connect_message

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
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

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
            return TheHiveWrapper.unable_to_connect_message

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
                        {"_name": "getTask", "idOrName": task_id},
                        {"_name": "logs"},
                    ]
                },
            )

            output = []
            for log in response.json():
                formatted = self.format_response(log)
                output.append(formatted)

            return {"task_logs": output}
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

        except requests.exceptions.JSONDecodeError:
            return {
                "error": "The SOAR URL provided does not provide a valid data format. Please make sure that the soar is running on the URL."
            }

    def create_task_log(self, task_id, message):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/task/{task_id}/log"
            requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "message": message,
                },
            )
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def update_task_log(self, log_id, message):
        url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/log/{log_id}"
        try:
            requests.patch(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "message": message,
                },
            )
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

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
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def get_page(self, page_id: str | None = None):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            # Build the query
            query = {"query": [{"_name": "getPage", "idOrName": page_id}]}

            response = requests.post(url, headers=headers, json=query)

            output = []
            for page_data in response.json():
                formatted = self.format_response(page_data)
                output.append(
                    {
                        "id": formatted["id"],
                        "createdBy": formatted["createdBy"],
                        "createdAt": formatted["createdAt"],
                        "title": formatted["title"],
                        "content": formatted["content"],
                        "category": formatted["category"],
                    }
                )

            return {"message": "Success", "pages": output}

        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def get_pages(self, org_id: str | None = None, case_id: str | None = None):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/query"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            if org_id:
                headers["X-Organisation"] = f"{org_id}"

            # Build the query
            query = {"query": []}
            if case_id:
                query["query"].append({"_name": "getCase", "idOrName": case_id})
                query["query"].append({"_name": "pages"})
            else:
                query["query"].append({"_name": "listPage"})

            response = requests.post(url, headers=headers, json=query)

            output = []
            for page_data in response.json():
                formatted = self.format_response(page_data)
                output.append(
                    {
                        "id": formatted["id"],
                        "createdBy": formatted["createdBy"],
                        "createdAt": formatted["createdAt"],
                        "title": formatted["title"],
                        "content": formatted["content"],
                        "category": formatted["category"],
                    }
                )

            return {"message": "Success", "pages": output}

        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def create_page(self, title: str, content: str, category: str):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/page"
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "title": title,
                    "content": content,
                    "category": category,
                },
            ).json()

            return {"message": "Success", "id": response["_id"]}
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def update_page(
        self,
        page_id: str,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
    ):
        data = dict()
        if title:
            data["title"] = title
        if content:
            data["content"] = content
        if category:
            data["category"] = category

        try:
            url = (
                f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/page/{page_id}"
            )
            requests.patch(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=data,
            )
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def delete_page(self, page_id: str):
        try:
            url = (
                f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/page/{page_id}"
            )
            response = requests.delete(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def create_page_in_case(
        self,
        case_id: str,
        title: str,
        content: str,
        category: str,
        org_id: str | None = None,
    ):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/case/{case_id}/page"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            if org_id:
                headers["X-Organisation"] = f"{org_id}"
            response = requests.post(
                url,
                headers=headers,
                json={
                    "title": title,
                    "content": content,
                    "category": category,
                },
            ).json()

            return {"message": "Success", "id": response["_id"]}
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def update_page_in_case(
        self,
        case_id: str,
        page_id: str,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        org_id: str | None = None,
    ):
        data = dict()
        if title:
            data["title"] = title
        if content:
            data["content"] = content
        if category:
            data["category"] = category

        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/case/{case_id}/page/{page_id}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            if org_id:
                headers["X-Organisation"] = f"{org_id}"
            requests.patch(
                url,
                headers=headers,
                json=data,
            )
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message

    def delete_page_in_case(
        self, case_id: str, page_id: str, org_id: str | None = None
    ):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}api/v1/case/{case_id}/page/{page_id}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            if org_id:
                headers["X-Organisation"] = f"{org_id}"
            requests.delete(
                url,
                headers=headers,
            )
            return TheHiveWrapper.success_message
        except requests.exceptions.ConnectionError:
            return TheHiveWrapper.unable_to_connect_message
