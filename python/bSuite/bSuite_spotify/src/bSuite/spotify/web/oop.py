import browser_cookie3
import requests
from typing import Optional, TypedDict, Any, Union
from http.cookiejar import CookieJar

from .temp import tz_ts
from .exceptions import TokenError, EndpointError, CookieFailure, StoreError


def get_cookie(jar: CookieJar, key: Any):
    if not (found := next((x for x in jar if x.name == key), None)):
        return None
    return found.value


class StorableRWAT(TypedDict):
    token: str
    expires: int
    sp_dc: str


class RefreshingWebAccessToken:
    _refresh_url = 'https://open.spotify.com/get_access_token?reason=transport&productType=web_player'

    @classmethod
    def from_store(cls, store: StorableRWAT):
        self = cls(store['sp_dc'])
        self._token = store['token']
        self._expires = store['expires']
        return self

    def __init__(self, sp_dc: str | CookieJar):
        self._cookie = {'sp_dc': sp_dc} if isinstance(sp_dc, str) else sp_dc
        self._token: Union[str, None] = None
        self._expires: Union[int, None] = None

    def as_storable(self) -> StorableRWAT:
        if not (tok := self.token):
            raise StoreError()

        sp_dc = get_cookie(self._cookie, 'sp_dc') if isinstance(self._cookie, CookieJar) else self._cookie.get('sp_dc')
        return StorableRWAT(token=tok, expires=self._expires, sp_dc=sp_dc)

    @property
    def expiring(self):
        return (self._expires - tz_ts(True)) < 5_000 * 60

    @property
    def token(self):
        if not self._token or self.expiring:
            self._refresh()
        return self._token

    def _refresh(self):
        print('fetching new token')
        resp = requests.get(self._refresh_url, cookies=self._cookie)

        if not resp.ok:
            raise TokenError()

        if not isinstance(self._cookie, CookieJar):
            self._cookie = resp.cookies

        data = resp.json()
        self._token = data.get('accessToken')
        self._expires = data.get('accessTokenExpirationTimestampMs')
        print(f'new token expires at: {self._expires} or in: {(self._expires - tz_ts(True)) / 1000 / 60}m')


class WebAPIClient:
    """Spotify Web API client for hidden endpoints with built-in refreshing access token"""

    @classmethod
    def from_firefox(cls):
        browser = browser_cookie3.Firefox(domain_name='.spotify.com')
        cookies = browser.load()
        sp_dc = next((x for x in cookies if x.name == 'sp_dc'), None)
        if not sp_dc:
            raise CookieFailure()

        jar = CookieJar()
        jar.set_cookie(sp_dc)

        return cls(jar)

    def __init__(self, auth: str | CookieJar | RefreshingWebAccessToken):
        self.token = self._validate_auth(auth)
        self._id = None

    @staticmethod
    def _validate_auth(auth: str | CookieJar | RefreshingWebAccessToken):
        if isinstance(auth, RefreshingWebAccessToken):
            return auth
        elif isinstance(auth, str | CookieJar):
            return RefreshingWebAccessToken(auth)
        else:
            raise TypeError(auth)

    @property
    def id(self):
        if not self._id:
            self._id = self.current_user()['id']
        return self._id

    def _fetch(self, url: str, rsp_key: Optional[str] = None):
        resp = requests.get(
            url=url,
            headers={'Authorization': f'Bearer {self.token.token}'}
        )
        if not resp.ok:
            raise EndpointError()

        data = resp.json()
        return data.get(rsp_key) if rsp_key else data

    def current_user(self):
        url = 'https://api.spotify.com/v1/me'
        return self._fetch(url)

    def activity(self):
        url = 'https://guc-spclient.spotify.com/presence-view/v1/buddylist'
        return self._fetch(url, 'friends')

    def following(self, alt_user: Optional[str] = None):
        user = alt_user if alt_user else self.id
        url = f'https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user}/following?market=from_token'
        return self._fetch(url, 'profiles')

    def followers(self, alt_user: Optional[str] = None):
        user = alt_user if alt_user else self.id
        url = f'https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user}/followers?market=from_token'
        return self._fetch(url, 'profiles')
