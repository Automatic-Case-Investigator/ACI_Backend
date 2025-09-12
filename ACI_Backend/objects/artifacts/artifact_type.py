from enum import Enum

class ArtifactType(Enum):
    IP = "ip"
    HASH = "hash"
    EMAIL = "email"
    URL = "url"
    DOMAIN = "domain"