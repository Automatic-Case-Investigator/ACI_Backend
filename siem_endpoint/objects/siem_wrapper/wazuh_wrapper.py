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
            response = requests.post(
                url, headers=headers, json=query, verify=False
            ).json()

            hits = []
            if "hits" in response:
                hits = response["hits"]["hits"]

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

    def _walk_properties(self, props, prefix=""):
        result = {}

        for name, value in props.items():
            field_path = f"{prefix}.{name}" if prefix else name

            # If the field has a type, record it
            if "type" in value:
                result[field_path] = value["type"]

            # If nested properties exist, recurse
            if "properties" in value:
                result.update(self._walk_properties(value["properties"], field_path))

            # Handle multi-fields (like keyword under text)
            if "fields" in value:
                for subname, subval in value["fields"].items():
                    if "type" in subval:
                        result[f"{field_path}.{subname}"] = subval["type"]

        return result

    def get_available_fields(self):
        try:
            url = f"{self.protocol}//{self.hostname}{self.base_dir}wazuh-alerts-*/_field_caps?fields=*"
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode("utf-8")
            headers = {
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/json",
            }
            response = requests.get(url, headers=headers, verify=False).json()

            field_map = {}
            for field in response["fields"]:
                first_key = next(iter(response["fields"][field]))
                aggregatable = response["fields"][field][first_key].get("aggregatable", False)
                field_map[field] = {
                    "type": response["fields"][field][first_key].get("type", "unknown"),
                    "searchable": response["fields"][field][first_key].get("searchable", False),
                    "aggregatable": aggregatable,
                }

            return field_map
        
        except requests.exceptions.ConnectionError as e:
            return WazuhWrapper.unable_to_connect_message
        
    def get_field_top_values(self, field: str, size: int = 10):
        url = f"{self.protocol}//{self.hostname}{self.base_dir}wazuh-alerts-*/_field_caps?fields=*"
        
        credentials = base64.b64encode(
            f"{self.username}:{self.password}".encode()
        ).decode("utf-8")
        
        headers = {
            "Authorization": "Basic " + credentials,
            "Content-Type": "application/json",
        }
        
        agg_query = {
            "size": 0,
            "aggs": {
                "field_counts": {
                    "terms": {
                        "field": field,
                        "size": size,
                    }
                }
            },
        }
        agg_url = f"{self.protocol}//{self.hostname}{self.base_dir}wazuh-alerts-*/_search"
        
        agg_response = requests.post(
            agg_url, headers=headers, json=agg_query, verify=False
        ).json()
        
        buckets = (
            agg_response.get("aggregations", {})
            .get("field_counts", {})
            .get("buckets", [])
        )
        
        return [{"key": bucket["key"], "count": bucket["doc_count"]} for bucket in buckets]

    def get_field_count(self, field: str):
        try:
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode("utf-8")

            headers = {
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/json",
            }

            count_query = {
                "query": {
                    "exists": {
                        "field": field,
                    }
                }
            }

            count_url = (
                f"{self.protocol}//{self.hostname}{self.base_dir}wazuh-alerts-*/_count"
            )
            count_response = requests.post(
                count_url, headers=headers, json=count_query, verify=False
            ).json()

            return count_response.get("count", 0)
        except requests.exceptions.ConnectionError:
            return WazuhWrapper.unable_to_connect_message

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
            response = requests.post(
                url, headers=headers, json=query, verify=False
            ).json()

            hits = []
            if "hits" in response:
                hits = response["hits"]["hits"]
                
            print(id, len(hits))
            if len(hits) == 0:
                return {"result": dict()}

            return {"result": hits[0]}

        except requests.exceptions.ConnectionError as e:
            return WazuhWrapper.unable_to_connect_message

    def fix_curly_brace_mismatch(self, query: str) -> str:
        open_count = query.count("{")
        close_count = query.count("}")

        # If there are more closing braces than opening braces
        if close_count > open_count:
            excess = close_count - open_count

            # Remove excess closing braces from the end only
            i = len(query) - 1
            while i >= 0 and excess > 0:
                if query[i] == "}":
                    query = query[:i] + query[i + 1 :]
                    excess -= 1
                i -= 1

        return query

    def format_query(self, query: str) -> str:
        query = self.fix_curly_brace_mismatch(query)
        query_dict = json.loads(query)

        return json.dumps({"query": query_dict["query"]})

    def parse_queries_from_task_log(self, task_log_str: str):
        matches = re.finditer(r"^[-*•]\s*(.+)$", task_log_str, flags=re.MULTILINE)
        queries = []

        for match in matches:
            point = match.group(1)
            start_pos = match.start(1)
            end_pos = match.end(1)

            try:
                query = self.format_query(point)
                queries.append(
                    {"query": query, "start_pos": start_pos, "end_pos": end_pos}
                )
            except json.JSONDecodeError:
                print("Warning: Bulletpoint format must be JSON, ignoring bulletpoint")

        return queries
