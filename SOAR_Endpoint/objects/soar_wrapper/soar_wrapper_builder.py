import sys
from .thehive_wrapper import TheHiveWrapper


class SOARWrapperBuilder:
    SOAR_CHOICES = ["TH"]

    build_functions = [
        lambda protocol, hostname, base_dir, api_key: TheHiveWrapper(
            protocol,
            hostname,
            base_dir,
            api_key,
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

    def setHostname(self, hostname):
        self.hostname = hostname
        return self

    def setBaseDir(self, base_dir):
        self.base_dir = base_dir
        return self

    def setAPIKey(self, api_key):
        self.api_key = api_key
        return self

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
                        hostname=self.hostname,
                        base_dir=self.base_dir,
                        api_key=self.api_key,
                    )
                except TypeError as e:
                    raise TypeError("Incorrect SOAR information")
