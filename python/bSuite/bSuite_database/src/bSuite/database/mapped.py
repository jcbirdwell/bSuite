import json
import pickle as pk
from typing import Any, Generator

from .base import CoreDatabase
from collections.abc import MutableMapping


class MappedDatabase(CoreDatabase, MutableMapping):
    """
    Interface that allows for a database table to be interacted with as if it were a dictionary object.
    """
    # TODO: add a mode selector pickle v json
    def __init__(self, cxn_config: dict, table: str, pickle=False):
        self.bound_table = table
        self._pickle = pickle
        if self._pickle:
            print('WARNING: Pickle mode is active. Not for use in production. Learn more about pickle '
                  'vulnerabilities here: https://docs.python.org/3/library/pickle.html')
        self._vk = 'val_p' if self._pickle else 'val'
        super().__init__(cxn_config)

    def __repr__(self):
        return f'Mutable mapping interface bound to table "{self.bound_table}" of database "{self.db}".'

    def __post_init__(self):
        super().__post_init__()
        print(f'ensuring {self.bound_table} in database:', self.tables)
        if self.bound_table not in self.tables:
            print('generating table')
            tq = f"""
            create table {self.bound_table} (
                var varchar(255) primary key,
                val jsonb,
                val_p bytea,
                ts timestamp default current_timestamp
            );
            """

            # add table
            self.query(tq, no_resp=True)

            # clear cached table names
            self._tables = None

    def dumps(self, v) -> bytes | str:
        if self._pickle:
            return pk.dumps(v)
        return json.dumps(v)

    @staticmethod
    def loads(v) -> Any:
        if isinstance(v, memoryview):
            return pk.loads(v)
        return v

    def __setitem__(self, __k: Any, __v: Any) -> None:
        self.insert(self.bound_table, {'var': __k, self._vk: self.dumps(__v)}, upsert_on='var')

    def __delitem__(self, __v: Any) -> None:
        self.delete(self.bound_table, {self._vk: self.dumps(__v)})

    def __getitem__(self, __k: Any) -> Any:
        resp = self.select(self.bound_table, self._vk, where={'var': __k}, limit=1)

        # throw missing
        if not resp:
            raise KeyError(f'{__k} not present.')

        # enable de-pickling via parse
        return self.loads(resp[0])

    def __len__(self) -> int:
        resp = self.select(self.bound_table, f'count({self._vk})')
        return resp[0] if resp else 0

    def __iter__(self) -> Generator:
        for x in self.select(self.bound_table, 'var', where={self._vk: 'not null'}):
            yield x
