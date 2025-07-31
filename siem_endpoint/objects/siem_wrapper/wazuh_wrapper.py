from .siem_wrapper import SIEMWrapper
import requests
import base64
import json
import re
import traceback


class WazuhWrapper(SIEMWrapper):
    def __init__(
        self,
        protocol: str,
        name: str,
        hostname: str,
        base_dir: str,
        use_api_key: bool,
        api_key: str,
        username: str,
        password: str,
    ):
        super().__init__(
            protocol,
            name,
            hostname,
            base_dir,
            use_api_key,
            api_key,
            username,
            password,
        )
        if use_api_key or (username == "" and password == ""):
            print("Wazuh accepts only username and password authentication")

    def query(self, query_str: str, output_full: bool = False):
        try:
            query = json.loads(query_str)
            url = f"{self.protocol}//{self.hostname}{self.base_dir}wazuh-alerts-*/_search?pretty"
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode("utf-8")
            headers = {
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/json",
            }
            response = requests.post(url, headers=headers, json=query, verify=False)
            response_json = response.json()
            print(f"Query: {query_str}\nResponse: {response_json}")
            hits = response_json["hits"]["hits"]

            if output_full:
                return {"results": hits}

            output = []
            for hit in hits:
                output.append(hit["_id"])

            return {"results": output}
        
        except KeyError:
            return WazuhWrapper.unable_to_connect_message
        
        except requests.exceptions.ConnectionError as e:
            return WazuhWrapper.unable_to_connect_message
        
        except json.JSONDecodeError:
            print(traceback.format_exc())
            return {"error": "Invalid query format"}

    def get_event(self, id: str):
        try:
            query = {"query": {"match": {"_id": id}}}
            url = f"{self.protocol}//{self.hostname}{self.base_dir}wazuh-alerts-*/_search?pretty"
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode("utf-8")
            headers = {
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/json",
            }
            response = requests.post(url, headers=headers, json=query, verify=False)
            hits = response.json()["hits"]["hits"]

            return {"result": hits[0]}

        except requests.exceptions.ConnectionError as e:
            return WazuhWrapper.unable_to_connect_message
        
        
    def parse_queries_from_task_log(self, task_log_str: str):
        matches = re.finditer(r"^[-*•]\s*(.+)$", task_log_str, flags=re.MULTILINE)
        queries = []

        for match in matches:
            point = match.group(1)
            start_pos = match.start(1)
            end_pos = match.end(1)

            try:
                json.loads(point)
                queries.append({
                    "query": point,
                    "start_pos": start_pos,
                    "end_pos": end_pos
                })
            except json.JSONDecodeError:
                try:
                    json.loads(point)
                    queries.append({
                        "query": point,
                        "start_pos": start_pos,
                        "end_pos": end_pos
                    })
                except json.JSONDecodeError:
                    print("Warning: Bulletpoint format must be JSON, ignoring bulletpoint")
                    pass

        return queries
