import sys
from .thehive_wrapper import TheHiveWrapper


class SOARWrapperBuilder:
    SOAR_CHOICES = ["TH"]

    build_functions = [
        lambda protocol, name, hostname, base_dir, api_key: TheHiveWrapper(
            protocol=protocol,
            name=name,
            hostname=hostname,
            base_dir=base_dir,
            api_key=api_key,
        )
    ]

    def __init__(
        self, soar_type=None, protocol=None, hostname=None, base_dir=None, api_key=None
    ):
        self.soar_type = soar_type
        self.protocol = protocol
        self.hostname = hostname
        self.base_dir = base_dir
        self.api_key = api_key

    def setSOARType(self, soar_type):
        self.soar_type = soar_type
        return self

    def setProtocol(self, protocol):
        self.protocol = protocol
        return self

    def setName(self, name):
        self.name = name
        return self
    
    def setHostname(self, hostname):
        self.hostname = hostname
        return self

    def setBaseDir(self, base_dir):
        self.base_dir = base_dir
        return self

    def setAPIKey(self, api_key):
        self.api_key = api_key
        return self
    
    def build_from_model_object(self, soar_info_obj):
        self.setName(soar_info_obj.name)
        self.setSOARType(soar_info_obj.soar_type)
        self.setProtocol(soar_info_obj.protocol)
        self.setHostname(soar_info_obj.hostname)
        self.setBaseDir(soar_info_obj.base_dir)
        self.setAPIKey(soar_info_obj.api_key)
        return self.build()
        
    def build(self):
        for i in range(len(self.SOAR_CHOICES)):
            if self.soar_type == self.SOAR_CHOICES[i]:
                error_msgs = []
                if self.protocol == None or self.protocol == "":
                    error_msgs.append("Missing protocol information")
                if self.hostname == None or self.protocol == "":
                    error_msgs.append("Missing hostname information")
                if self.base_dir == None or self.protocol == "":
                    error_msgs.append("Missing base_dir information")
                if self.api_key == None or self.protocol == "":
                    error_msgs.append("Missing api_key information")

                if len(error_msgs) != 0:
                    raise TypeError(", ".join(error_msgs))

                try:
                    return self.build_functions[i](
                        protocol=self.protocol,
                        name=self.name,
                        hostname=self.hostname,
                        base_dir=self.base_dir,
                        api_key=self.api_key,
                    )
                except TypeError as e:
                    raise TypeError("Incorrect SOAR information. Please make sure your entered information that is supported by the system.")
                
        raise TypeError("Incorrect SOAR information. Please make sure your entered information that is supported by the system.")
