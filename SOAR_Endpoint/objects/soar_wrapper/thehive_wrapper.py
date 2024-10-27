from .soar_wrapper import SOARWrapper

class TheHiveWrapper(SOARWrapper):
    def __init__(self, protocol, hostname, base_dir, api_key):
        SOARWrapper.__init__(protocol, hostname, base_dir, api_key)
        