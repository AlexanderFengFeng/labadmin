#!/usr/bin/env python

import os
from os.path import join, dirname, abspath, exists
from future import standard_library
with standard_library.hooks():
    from configparser import (ConfigParser, NoOptionError,
                              MissingSectionHeaderError)


DEFAULT_CONFIG_FP = join(dirname(abspath(__file__)), '../config.txt')


class KniminConfig(object):
    """Holds the configuration information

    Parameters
    ----------
    config_fp: str, optional
        Filepath to the configuration file

    Attributes
    ----------
    debug : bool
        If in debug state
    user : str
        The postgres user
    password : str
        The postgres password for the previous user
    database : str
        The postgres database to connect to
    host : str
        The host where the database lives
    port : int
        The port used to connect to the postgres database in the previous host

    Notes
    -----
    ConfigurationManager base sourced from the QIITA project
    """
    config_fp = os.environ.get('KNIMIN_CONFIG_FP', DEFAULT_CONFIG_FP)

    def __init__(self, config_fp=None):
        if config_fp is None:
            config_fp = self.config_fp

        if not os.path.exists(config_fp):
            raise IOError('Config file %s missing!' % config_fp)

        config = ConfigParser()
        with open(config_fp, 'U') as conf_file:
            config.readfp(conf_file)

        _expected_sections = {'main', 'postgres'}
        if set(config.sections()) != _expected_sections:
            missing = _expected_sections - set(config.sections())
            raise ValueError("Missing sections: %s" % missing)

        self._get_main(config)
        self._get_postgres(config)

    def _get_main(self, config):
        """Get the configuration of the main section"""
        self.debug = config.getboolean('main', 'debug')

    def _get_postgres(self, config):
        """Get the configuration of the postgres section"""
        self.user = config.get('postgres', 'user')
        self.password = config.get('postgres', 'password')
        self.database = config.get('postgres', 'database')
        self.host = config.get('postgres', 'host')
        self.port = config.getint('postgres', 'port')
