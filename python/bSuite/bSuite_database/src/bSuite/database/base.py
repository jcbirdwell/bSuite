from contextlib import contextmanager
from typing import Generator, Optional
from psycopg2.extensions import cursor
from psycopg2.pool import ThreadedConnectionPool
from os import environ as env


def get_comparator(v) -> str | tuple:
    if isinstance(v, str):
        if 'null' in v:
            return ('is not', None) if 'not' in v else ('is', None)
        return 'like'
    elif isinstance(v, int):
        return '='

    return 'is'


class CoreDatabase:
    """
    Base interface for postgres database, includes methods for
    querying, selection, insertion, and deletion
    """

    @classmethod
    def from_env(cls,
                 etc: Optional[dict] = None,
                 verbose: Optional[bool] = False
                 ):
        """
        Automatically pull basic connection parameters [host, port, database, user, and password]
        from the environmental variables (caps and prefixed with DB_ ex: DB_HOST) and return a database instance.
        Can be provided with a dict of additional connection parameters which will override
        values from the environment or be appended if not present.

        Parameters
        ----------
        etc : dict
            additional connection parameters used to override/add to environmental variables.
        verbose : bool
            provides variable parsing output
        Returns
        -------
        CoreDatabase
            A core database instance with connection parameters from the environment.
        """

        def v_print(*s):
            if verbose:
                print(*s)

        v_print('Building database connection parameters from env...')
        missing = [x for x in ['DB_HOST', 'DB_PORT', 'DB_DATABASE', 'DB_USER', 'DB_PASSWORD'] if x not in env]
        v_print('env missing: ', missing, 'using default values for these fields.')

        # build base connection parameters, filling where needed
        cxn = {
            'host': env.get('DB_HOST', 'localhost'),
            'port': env.get('DB_PORT', 5432),
            'database': env.get('DB_DATABASE', 'postgres'),
            'user': env.get('DB_USER', 'postgres'),
            'password': env.get('DB_PASSWORD', None)
        }

        # merge with overrides if needed
        if etc:
            v_print(f'received additional config. '
                    f'adding: {[x for x in etc if x not in cxn]} '
                    f'overwriting: {[x for x in etc if x in cxn]}')

            cxn = cxn | etc

        v_print(f'Finalized connection parameters: ', cxn)

        return cls(cxn)

    def __init__(self, cxn_config: dict):
        # parse connection parameters from ini file and merge
        # with overrides if provided
        self.db = None
        self._tables = None
        self.config = cxn_config
        self.pool = ThreadedConnectionPool(1, 5, **self.config)
        self.__post_init__()

    def __post_init__(self):
        self.db = self.query('SELECT current_database()', as_tuple=True)[0]

    @contextmanager
    def cursor(self) -> Generator[cursor, None, None]:
        """
        Enable auto-magic cursor formation from pool, commit,
        and return via context management.

        Returns
        -------
        Generator
            temporary cursor object
        """

        # Pull cxn from pool
        cxn = self.pool.getconn()
        cxn.autocommit = True
        curs: cursor = cxn.cursor()

        try:
            # Provide
            yield curs
        finally:
            # Cleanup on context end
            cxn.commit()
            curs.close()
            cxn.close()
            self.pool.putconn(cxn)

    def query(self,
              query: str,
              vals: tuple | None = None,
              as_tuple: bool | None = False,
              no_resp: bool | None = False
              ) -> list:
        """
        Committed database query execution

        Parameters
        ----------
        query : str
            the command to be executed
        vals : tuple
            parameterized values to be included with query if applicable
            (default=None)
        as_tuple : bool
            modify return value to be a tuple list instead of dict
        no_resp : bool
            whether to attempt to fetch and parse execution output,
            ie from a select query (default=False)

        Returns
        -------
        list
            Record-like dict list when resp specified
        """

        fetched, cols = [], []

        # execute with temp cursor
        with self.cursor() as csr:
            csr.execute(query, vals)
            if not no_resp:
                # grab columns for record formation
                if not as_tuple:
                    cols = tuple(x[0] for x in csr.description)
                # retrieve values
                fetched = csr.fetchall()

        # cursor returned to pool before parsing, if required.
        if fetched:
            if cols:
                return [{k: v for k, v in zip(cols, row)} for row in fetched]
            elif as_tuple:
                return [x for x in fetched]

    @property
    def tables(self):
        if not self._tables:
            q = "select table_name from information_schema.tables where table_schema = 'public'"
            resp = self.query(q, as_tuple=True)
            self._tables = [x[0] for x in resp if x] if resp else []
        return self._tables

    def select(self, table: str, field='*', where: dict | None = None, limit=None) -> list | None:
        """
        Fetch rows from a database table within specified fields

        Parameters
        ----------
        table : str
            a valid table reference within the initialized database
        field : str
            valid sql field selector str
        where : dict
            passable dict of where results are query results of matching k, v pairs
        limit : int
            set max items, None returns all (default None)

        Returns
        -------
        list:
            Record-like list of dicts keyed to table fields

        """
        if table not in self.tables:
            raise KeyError(f'Table "{table}" is unavailable in current database.')

        # set where params
        passed_vars = []
        if not where:
            where = ''
        else:
            conditions = []
            for k, v in where.items():
                comparator = get_comparator(v)
                if isinstance(comparator, tuple):
                    comparator, v = comparator

                conditions.append(f'{k} {comparator} %s')
                passed_vars.append(v)
            where = f" where {' and '.join(conditions)}"

        # prepare parameterized values to be passed to query when present
        passed_vars = None if not passed_vars else tuple(passed_vars)

        # modify or remove limit if specified
        limit = f' limit {limit}' if limit else ''

        # form full query str
        q = f'select {field} from {table}{where}{limit};'

        # identify if values should be returned as a dict or singleton list
        single = field != '*' and field.find(',') == -1

        # execute, requesting a tuple (field parsing skipped) if allowable
        resp = self.query(q, vals=passed_vars, as_tuple=single)

        # early return to escape NoneType iteration error
        if not resp:
            return []

        # forcing return as a list, for some reason (probably the cursor being
        # a generator), its returning and iterable.
        return [x[0] for x in resp] if single else [x for x in resp]

    def insert(self, table: str, data: dict | list, upsert_on: str | None = None) -> None:
        """
        Fast parameterized insertion

        Parameters
        ----------
        table : str
            target for data entry
        data : dict
            insertion data in record format, with keys matching
            specified table fields.
        upsert_on : str
            unique column key for which collisions result in an update (default = None)

        Raises
        ------
        psycopg2.errors.UndefinedTable
            on invalid table
        psycopg2.errors.UndefinedColumn
            on invalid fields

        Returns
        -------
        None
            None
        """

        # force list
        data = [data] if isinstance(data, dict) else data

        # extract keys from first - data uniformity is assumed, could
        # be checked for with:
        # kls = tuple(max(data, key=lambda x: len(data[x])).keys())
        kls = tuple(data[0].keys())

        # sql formatted table keys generated
        ks = f'({", ".join(kls)})'

        # build correct length parameterized variable (%s, %s, ...) strings
        kvs = f'({", ".join("%s" for _ in kls)})'

        # set entry variables
        vks = ', '.join(kvs for _ in data)

        # grab all values and flatten to tuple
        vs = tuple(z for x in data for z in x.values())
        # if previous data non-uniformity handling is implemented,
        # missing keys must instead be filled with:
        # vs = tuple(z for x in data for z in tuple(data[x].get(k, None) for k in kls))

        # set collision result
        ex_ks = f"({', '.join(f'EXCLUDED.{k}' for k in kls)})"
        collision = 'DO NOTHING' if not upsert_on else f"({upsert_on}) DO UPDATE SET {ks} = {ex_ks}"

        # full query formation
        q = f"insert into {table} {ks} VALUES {vks} ON CONFLICT {collision};"

        # submit for execution with parameterized values
        self.query(q, vs, no_resp=True)

    def delete(self, table: str, where: dict):

        conditions = []
        passed_vars = []
        for k, v in where.items():
            comparator = get_comparator(v)
            conditions.append(f'{k} {comparator} %s')
            passed_vars.append(v)
        where_conditions = f"{' and '.join(conditions)}"
        q = f'delete from {table} where {where_conditions}'
        self.query(q, vals=tuple(passed_vars), no_resp=True)
