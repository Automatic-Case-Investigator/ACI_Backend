from .siem_wrapper import SIEMWrapper
import requests
import base64
import json
import re


class WazuhWrapper(SIEMWrapper):
    unable_to_connect_message = {
        "error": "Unable to connect to the SIEM platform. Please make sure you have the correct connection settings."
    }
    
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

    def query(self, query_str: str):
        try:
            query = json.loads(query_str)
            url = f"{self.protocol}://{self.hostname}{self.base_dir}wazuh-alerts-*/_search?pretty"
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode("utf-8")
            headers = {
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/json",
            }
            response = requests.post(url, headers=headers, json=query, verify=False)
            hits = response.json()["hits"]["hits"]

            output = []
            for hit in hits:
                output.append(hit["_id"])

            return {"results": output}
        
        except requests.exceptions.ConnectionError as e:
            return WazuhWrapper.unable_to_connect_message
        
        except json.JSONDecodeError:
            return {"error": "Invalid query format"}

    def get_event(self, id: str):
        try:
            query = {"query": {"match": {"_id": id}}}
            url = f"{self.protocol}://{self.hostname}{self.base_dir}wazuh-alerts-*/_search?pretty"
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
        bulletpoints = re.findall(r"^[-*•]\s*(.+)$", task_log_str, flags=re.MULTILINE)
        queries = []
        
        for point in bulletpoints:
            try:
                json.loads(point)
                queries.append(point)
            except json.JSONDecodeError:
                pass
            
        return queries
        
