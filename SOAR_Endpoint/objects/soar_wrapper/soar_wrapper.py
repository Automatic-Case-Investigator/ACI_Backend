class SOARWrapper:
    def __init__(self, protocol, hostname, base_dir, api_key):
        self.protocol = protocol
        self.hostname = hostname
        self.base_dir = base_dir
        self.api_key = api_key
        
    def get_case(self, case_id):
        print("To be implemented")