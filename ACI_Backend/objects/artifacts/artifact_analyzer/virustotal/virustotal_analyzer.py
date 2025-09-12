from ACI_Backend.objects.artifacts.artifact_analyzer.analyzer import Analyzer
from ACI_Backend.objects.artifacts.artifact_type import ArtifactType
import requests
import warnings
import time
import os


class VirustotalAnalyzer(Analyzer):
    supported_datatypes: set[ArtifactType] = {
        ArtifactType.DOMAIN,
        ArtifactType.IP,
        ArtifactType.URL,
        ArtifactType.HASH,
    }

    def __init__(self, api_key=""):
        self.api_key = (
            os.getenv("VIRUSTOTAL_API_KEY") if len(self.api_key) == 0 else api_key
        )
        self.base_url = "https://www.virustotal.com"
        self.analyze_fn = {
            ArtifactType.DOMAIN: self.analyze_domain,
            ArtifactType.IP: self.analyze_ip,
        }

    def analyze_domain(self, data: str):
        url = f"{self.base_url}/api/v3/domains/{data}"
        headers = {"accept": "application/json", "x-apikey": self.api_key}
        response = requests.get(url, headers=headers)
        return response.json()

    def analyze_ip(self, data: str):
        url = f"{self.base_url}/api/v3/ip_addresses/{data}"
        headers = {"accept": "application/json", "x-apikey": self.api_key}
        response = requests.get(url, headers=headers)
        return response.json()

    def analyze_hash(self, data: str):
        url = f"{self.base_url}/api/v3/files/{data}"
        headers = {"accept": "application/json", "x-apikey": self.api_key}
        response = requests.get(url, headers=headers)
        return response.json()

    def analyze_url(self, data: str):
        analyze_form_data = {"url": data}
        analyze_headers = {
            "accept": "application/json",
            "x-apikey": self.api_key,
            "content-type": "application/x-www-form-urlencoded",
        }
        analyzer_url = f"{self.base_url}/api/v3/urls"
        analyzer_call_details = requests.post(
            analyzer_url, data=analyze_form_data, headers=analyze_headers
        ).json()

        if "error" in analyzer_call_details:
            return analyzer_call_details

        analysis_id = analyzer_call_details["data"]["id"]

        timeout_message = f"Analysis for url {data} timed out"
        start = time.time()
        while True:
            result = self.get_analysis(analysis_id)
            status = result["data"]["attributes"]["status"]
            if status != "queued":
                return result
            if time.time() - start > 20:
                warnings.warn(timeout_message)
                break
            time.sleep(1)

        return {"error": {"message": timeout_message}}

    def get_analysis(self, id: str):
        url = f"{self.base_url}/api/v3/analyses/{id}"
        headers = {"accept": "application/json", "x-apikey": self.api_key}
        response = requests.get(url, headers=headers)
        return response.json()

    def analyze_artifact(self, data: str, datatype: ArtifactType):
        if datatype not in self.analyze_fn:
            warnings.warn(f"Analysis for artifact type {datatype} is not implemented")
            return

        return self.analyze_fn[datatype](data)
