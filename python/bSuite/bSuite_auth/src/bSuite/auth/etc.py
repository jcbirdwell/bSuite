from typing import Literal, TypedDict


AvailableEndpoints = Literal[
    'activeKey',
    'credential',
    'retrieveToken',
    'logout'
]


class FailedAuth(Exception):
    def __init__(self, *args):
        super().__init__(self, *args)


class RevokedAuth(Exception):
    def __init__(self, *args):
        super().__init__(self, *args)


class PreppedAuth(TypedDict):
    """Object containing the authorization url for client login and its associated reference string."""
    ref: str
    url: str
