from .siem_wrapper import SIEMWrapper
import requests
import base64
import json
import re
import traceback


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
        
    
    def fix_json_braces(self, json_str):
        """Fix unbalanced braces/brackets in JSON strings."""
        stack = []
        quotes = False
        fixed = list(json_str)
        
        for i, char in enumerate(json_str):
            if char == '"' and (i == 0 or json_str[i-1] != '\\'):
                quotes = not quotes
            if quotes:
                continue
                
            if char in '{[':
                stack.append(char)
            elif char in '}]':
                if not stack:
                    fixed.pop(i)
                    continue
                last_open = stack.pop()
                if (char == '}' and last_open != '{') or (char == ']' and last_open != '['):
                    fixed[i] = '}' if last_open == '{' else ']'
        
        while stack:
            last_open = stack.pop()
            fixed.append('}' if last_open == '{' else ']')
        
        return ''.join(fixed)
        
    def parse_queries_from_task_log(self, task_log_str: str):
        matches = re.finditer(r"^[-*•]\s*(.+)$", task_log_str, flags=re.MULTILINE)
        queries = []

        for match in matches:
            point = match.group(1)
            start_pos = match.start(1)  # start index of the actual point (without bullet)
            end_pos = match.end(1)      # end index of the actual point

            try:
                json.loads(point)
                queries.append({
                    "query": point,
                    "start_pos": start_pos,
                    "end_pos": end_pos
                })
            except json.JSONDecodeError:
                point = self.fix_json_braces(point)
                try:
                    json.loads(point)
                    queries.append({
                        "query": point,
                        "start_pos": start_pos,
                        "end_pos": end_pos
                    })
                except json.JSONDecodeError:
                    pass

        return queries
