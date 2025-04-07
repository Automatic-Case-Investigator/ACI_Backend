from .wazuh_wrapper import WazuhWrapper


class SIEMWrapperBuilder:
    SIEM_CHOICES = ["WZ"]

    build_functions = [
        lambda protocol, name, hostname, base_dir, use_api_key, api_key, username, password: WazuhWrapper(
            protocol=protocol,
            name=name,
            hostname=hostname,
            base_dir=base_dir,
            use_api_key=use_api_key,
            api_key=api_key,
            username=username,
            password=password,
        )
    ]

    def __init__(
        self,
        siem_type: str = None,
        protocol: str = None,
        hostname: str = None,
        base_dir: str = None,
        use_api_key: bool = None,
        api_key: str = None,
        username: str = None,
        password: str = None,
    ):
        self.siem_type = siem_type
        self.protocol = protocol
        self.hostname = hostname
        self.base_dir = base_dir
        self.use_api_key = use_api_key
        self.api_key = api_key
        self.username = username
        self.password = password

    def setSIEMType(self, siem_type: str):
        self.siem_type = siem_type
        return self

    def setProtocol(self, protocol: str):
        self.protocol = protocol
        return self

    def setName(self, name: str):
        self.name = name
        return self

    def setHostname(self, hostname: str):
        self.hostname = hostname
        return self

    def setAPIKeyEnabled(self, enabled: bool):
        self.use_api_key = enabled
        return self

    def setBaseDir(self, base_dir: str):
        self.base_dir = base_dir
        return self

    def setAPIKey(self, api_key: str):
        self.api_key = api_key
        return self

    def setUsernamePassword(self, username: str, password: str):
        self.username = username
        self.password = password

    def build_from_model_object(self, siem_info_obj):
        self.setName(siem_info_obj.name)
        self.setSIEMType(siem_info_obj.siem_type)
        self.setProtocol(siem_info_obj.protocol)
        self.setHostname(siem_info_obj.hostname)
        self.setBaseDir(siem_info_obj.base_dir)
        self.setAPIKeyEnabled(siem_info_obj.use_api_key)
        self.setAPIKey(siem_info_obj.api_key)
        self.setUsernamePassword(siem_info_obj.username, siem_info_obj.password)
        return self.build()

    def build(self):
        for i in range(len(self.SIEM_CHOICES)):
            if self.siem_type == self.SIEM_CHOICES[i]:
                error_msgs = []
                if self.protocol == None or self.protocol == "":
                    error_msgs.append("Missing protocol information")
                if self.hostname == None or self.hostname == "":
                    error_msgs.append("Missing hostname information")
                if self.base_dir == None or self.base_dir == "":
                    error_msgs.append("Missing base_dir information")
                if self.use_api_key:
                    if self.api_key == None or self.api_key == "":
                        error_msgs.append("Missing api_key information")
                else:
                    if self.username == None or self.username == "":
                        error_msgs.append("Missing username information")
                    if self.password == None or self.password == "":
                        error_msgs.append("Missing password information")

                if len(error_msgs) != 0:
                    raise TypeError(", ".join(error_msgs))

                try:
                    return self.build_functions[i](
                        protocol=self.protocol,
                        name=self.name,
                        hostname=self.hostname,
                        base_dir=self.base_dir,
                        use_api_key=self.use_api_key,
                        api_key=self.api_key,
                        username=self.username,
                        password=self.password,
                    )
                except TypeError as e:
                    raise TypeError(
                        "Incorrect SIEM information. Please make sure your entered information that is supported by the system."
                    )

        raise TypeError(
            "Incorrect SIEM information. Please make sure your entered information that is supported by the system."
        )
