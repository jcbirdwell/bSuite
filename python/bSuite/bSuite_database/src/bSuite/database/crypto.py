from .base import CoreDatabase
from cryptography.fernet import Fernet
from typing import Optional, Union
from os import environ as env


class AutoEncodeFernet(Fernet):
    def decrypt(self,
                token: Union[bytes, str, memoryview],
                ttl: Optional[int] = None
                ) -> str:
        """Modified decrypt method for processing memory-view object from database to a decoded str"""
        token = bytes(token) if isinstance(token, memoryview) else token
        return super().decrypt(token, ttl).decode()

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """Modified encryption method for accepting str objects"""
        data = data.encode() if isinstance(data, str) else data
        return super().encrypt(data)


class CryptoDatabase(CoreDatabase):
    @classmethod
    def env_key(cls, cxn_config: dict):
        """Method that allows for database cryptography key to be automatically
        pulled from environmental variable "CRYPTO_KEY" """
        crypto_key = env.get('CRYPTO_KEY')
        if not crypto_key:
            raise Exception('Environmental variable "CRYPTO_KEY" not found.')
        return cls(cxn_config, crypto_key)

    def __init__(self, cxn_config: dict, crypto_key: str | bytes):
        """
        Elevated database interface that allows for automatic encrypting and decrypting of
        specified database entries.

        Parameters
        ----------
        cxn_config : dict
            dictionary containing all database connection parameters (ie host, port, password, database)
        crypto_key : str | bytes
            32 character url-safe base64 encoded key to be used with encryption and decryption

        """
        super().__init__(cxn_config)
        self._crypt = AutoEncodeFernet(crypto_key)

    # TODO: instead parse tables and find which are marked as encrypted OR ask for all keys
    def crypt(self, p: dict | list[dict], client_key='client', secret_key='secret', rf_tk_key='refresh_token'):
        # save type for return value
        is_dict = isinstance(p, dict)
        # homogenize input
        p = [p] if is_dict else p

        # decrypt or encrypt method set on first use
        func = None
        # reduce to necessary keys
        ks = [k for k in [client_key, secret_key, rf_tk_key] if k in p[0]]
        for x in p:
            for k in ks:
                if v := x.get(k):
                    # set method if needed
                    if not func:
                        # auto-detects method based on type, encrypted data will be bytes
                        func_name = 'decrypt' if isinstance(v, memoryview) else 'encrypt'
                        func = getattr(self._crypt, func_name)

                    # gets method and calls with value
                    x[k] = func(v)
        return p[0] if is_dict else p
