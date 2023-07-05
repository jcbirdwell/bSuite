from configparser import ConfigParser
from os import environ as env


def config(file_path: str, section: str, env_overrides=False):
    """
    Parser for pulling config dict from a file, with optional env overriding to modify base configs or take their place.
    Environmental variables should take the form 'CONFIG_{section}_{key} = {value}'

    Parameters
    ----------
    file_path : str
        config file location
    section : str
        header name within config file
    env_overrides : bool
        allow environmental variables to update or extend base config pulled from provided file

    Returns
    -------
    dict
        containing key value pairs matching specified section of config file
    """

    parser = ConfigParser()
    parser.read(file_path)
    configs = {}

    if parser.has_section(section):
        # item tuples returned as dict
        configs = {k: v for k, v in parser.items(section)}
    if env_overrides:
        prefix = f'CONFIG_{section.upper}_'
        overrides = {k.removeprefix(prefix).lower(): v for k, v in env.items() if k.startswith(prefix)}
        configs = configs | overrides

    if configs:
        return configs

    raise Exception(f'Config missing for {section}')
