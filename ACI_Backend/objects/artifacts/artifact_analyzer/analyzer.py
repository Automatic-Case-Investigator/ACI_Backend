from ACI_Backend.objects.artifacts.artifact_type import ArtifactType
from abc import abstractmethod
import warnings

class Analyzer:
    supported_datatypes: set[ArtifactType] = {}
    
    def __init__(self):
        pass
        
    def run(self, data: str, datatype: ArtifactType):
        if datatype not in self.supported_datatypes:
            warnings.warn(f"Analysis for artifact type {datatype} is not implemented")
            return

        return self.run(data=data, datatype=datatype)
        
    @abstractmethod
    def analyze_artifact(self, data: str, datatype: ArtifactType):
        pass