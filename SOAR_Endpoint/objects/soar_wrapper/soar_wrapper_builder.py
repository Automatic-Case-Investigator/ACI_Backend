import sys
from .thehive_wrapper import TheHiveWrapper


class SOARWrapperBuilder:
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
        SOAR_CHOICES = [("TH", "The Hive")]
        for i in range(len(SOAR_CHOICES)):
            choice = SOAR_CHOICES[i]
            if self.soar_type == choice[0]:
                try:
                    return self.build_functions[i](
                        self.protocol, self.hostname, self.base_dir, self.api_key
                    )
                except TypeError:
                    break

        return None
