from typing import Literal, TypedDict


AvailableEndpoints = Literal[
    'activeKey',
    'credential',
    'retrieveToken',
    'logout'
]


class FailedAuth(Exception):
    """Authentication fetch failed"""


class RevokedAuth(Exception):
    """Access to provided token was revoked"""


class HostileEnvironment(Exception):
    """Missing environmental keys"""


class PreppedAuth(TypedDict):
    """Object containing the authorization url for client login and its associated reference string."""
    ref: str
    url: str
