# from .siem_wrapper import SIEMWrapper
from siem_wrapper import SIEMWrapper 
import requests
import base64
import json


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

    def query(self, query_str):
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
            print(response.json())

        except json.JSONDecodeError:
            return {"error": "Invalid query format"}
