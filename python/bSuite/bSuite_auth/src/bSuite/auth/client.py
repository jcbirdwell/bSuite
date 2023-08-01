import json
import base64
import requests

from typing import Optional
from os import environ as env

from fastapi import Request, Depends

from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives import hashes, serialization as cereal
from cryptography.exceptions import InvalidSignature

from .etc import AvailableEndpoints, FailedAuth, PreppedAuth, RevokedAuth, HostileEnvironment


class AuthClient:
    @classmethod
    def from_env(cls,
                 *void,
                 client_id: Optional[str] = None,
                 client_key: Optional[str] = None,
                 redirect_uri: Optional[str] = None,
                 allow_revalidation: Optional[bool] = False
                 ):
        """

        Parameters
        ----------
        void : any
            positional arguments not allowed.
        client_id : str
            optional client id override
        client_key : str
            optional api key override
        redirect_uri : str
            optional redirect overrides
        allow_revalidation : bool
            allow known keys to be revalidated instead of rebuilt

        Returns
        -------

        """

        client = client_id if client_id else env.get('AUTH_CLIENT_ID')
        key = client_key if client_key else env.get('AUTH_API_KEY')
        uri = redirect_uri if redirect_uri else env.get('AUTH_REDIRECT_URI')

        missing_envs = []
        if not client:
            missing_envs.append('AUTH_CLIENT_ID')
        if not key:
            missing_envs.append('AUTH_API_KEY')
        if not uri:
            missing_envs.append('AUTH_REDIRECT_URI')

        if missing_envs:
            raise HostileEnvironment(f'Cannot build auth client from environment. Missing variables: {missing_envs}.')

        return cls(client_id=client, client_key=key, redirect_uri=uri, allow_revalidation=allow_revalidation)

    def __init__(self, client_id: str, client_key: str, redirect_uri: str, allow_revalidation=False):
        self.id = client_id
        self.key = client_key
        self.redirect_uri = redirect_uri
        self.allow_revalidation = allow_revalidation
        self.auth = {'client_id': self.id, 'api_key': self.key}
        self.server = 'https://auth.brd.cx'
        self.core_encoding = ''
        self._public_key: RSAPublicKey | None = None
        self.padding = PSS(mgf=MGF1(hashes.SHA3_224()), salt_length=15)
        self.sha256 = hashes.SHA256()
        self.sessions = {}

    def user(self, request: Request) -> dict:
        bt_rf = request.cookies.get('bt_rf')
        current_user = request.cookies.get('user_id')
        if not bt_rf:
            user = None
        else:
            if not (user := self.sessions.get(bt_rf)) and self.allow_revalidation and current_user:
                pre_authed = self.full_fetch(bt_rf)
                if not pre_authed:
                    # invalidate?
                    user = None
                elif current_user == pre_authed['azp']['user_id']:
                    user = self.sessions[bt_rf] = {'pending': False, 'revalidated': True, **pre_authed['azp']}
        return user

    @staticmethod
    def b64_encode(data: str | bytes) -> str:
        return base64.urlsafe_b64encode(data.encode() if isinstance(data, str) else data).decode()

    @staticmethod
    def b64_decode(code: str) -> bytes:
        return base64.urlsafe_b64decode(code.encode())

    def _request(self,
                 endpoint: AvailableEndpoints,
                 params: dict | None = None,
                 body: dict | None = None,
                 raw=False
                 ):
        url = f'{self.server}/{endpoint}'
        if body:
            resp = requests.post(
                url=url,
                headers={'Content-Type': 'application/json'},
                json=body)
        else:
            resp = requests.get(url=url, params=params)
        if raw:
            return resp

        if resp.status_code == 200:
            try:
                return resp.json()
            except requests.exceptions.JSONDecodeError:
                return {'text': resp.text}

        raise FailedAuth({
            'url': url, 'body': body, 'params': params, 'request': vars(resp.request), 'response': vars(resp)
        })

    @property
    def public_key(self) -> RSAPublicKey:
        if not self._public_key:
            public_b64_str = self._request('activeKey').get('publicKey')
            public_pem = self.b64_decode(public_b64_str)
            self._public_key = cereal.load_pem_public_key(public_pem)

        return self._public_key

    def validate(self, bat: str, raw=False) -> dict | None:
        """Method for validating and extracting data from an encoded BAT received from the server"""
        if not bat:
            return None

        comps = bat.split('.')
        pack = bat[0:bat.rfind('.')]
        signature = comps[2]

        try:
            sig = self.b64_decode(signature)
            self.public_key.verify(sig, pack.encode(), self.padding, self.sha256)
            full_data = {
                'headers': json.loads(self.b64_decode(comps[0])),
                'data': json.loads(self.b64_decode(comps[1]))
            }
            return full_data if raw else full_data['data']
        except InvalidSignature:
            return None

    def invalidate_ref(self, ref: str) -> None:
        """The backend request involved in logging out a user."""
        body = {**self.auth, 'data': {'ref': ref}}
        self._request('logout', body=body)

    def fetch_ref(self) -> str:
        """Method for obtaining a raw reference string from the authentication server for given client"""
        return self._request('credential', params=self.auth).get('ref')

    def build_auth(self) -> PreppedAuth:
        """Fetches a reference string and builds an associated login url"""
        ref = self.fetch_ref()
        return {'ref': ref, 'url': f"{self.server}?ref={ref}&callback={self.redirect_uri}"}

    def retrieve(self, ref: str):
        p = {'client_id': self.id, 'api_key': self.key, 'ref': ref}
        resp = self._request('retrieveToken', params=p, raw=True)
        if resp.status_code == 200:
            return resp.json()['bat']
        elif resp.status_code == 403:
            raise RevokedAuth({'ref': ref})

    def full_fetch(self, ref: str):
        return self.validate(self.retrieve(ref))
