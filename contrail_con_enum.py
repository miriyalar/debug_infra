from enum import Enum
class ContrailConError(Enum):
    #Declar http error codes
    AUTH_FAILURE = 401
    GATEWAY_TIMEOUT = 503
    REDIRECTS = 301
