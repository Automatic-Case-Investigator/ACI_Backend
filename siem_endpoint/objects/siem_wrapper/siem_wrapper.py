class SIEMWrapper:
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
        self.protocol = protocol
        self.name = name
        self.hostname = hostname
        self.base_dir = base_dir
        self.use_api_key = use_api_key
        self.api_key = api_key
        self.username = username
        self.password = password

    def query(self, query_str):
        print("To be implemented")
