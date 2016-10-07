#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
 Default options for any debug vertex
"""

import argparse
import ConfigParser
import os

class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, **kwargs):
        super(ArgumentParser, self).__init__(**kwargs)
        self._parser_add_std_args()

    @staticmethod
    def read_config_option(config, section, option, default_option):
        ''' Read the config file. If the option/section is not present, return the default_option
        '''
        try:
            val = config.get(section, option)
            if val.lower() == 'true':
                val = True
            elif val.lower() == 'false' or val.lower() == 'none':
                val = False
            elif not val:
                val = default_option
            return val
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return default_option

    def _parser_add_std_args(self):
        self.add_argument("-c", "--config", help="Specify conf file", metavar="FILE", default='debug.ini')
        self.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true")
        self.add_argument("-d", "--discard", help="Disable dump of json output to file", action="store_true")
        self.add_argument("-D", "--depth", type=int, default=-1, help="Depth of the dependent vertexes to process")
        self.add_argument("-V", "--verify", help="Verify objects", action="store_true")
        self.add_argument("--username", help="stack username")
        self.add_argument("--password", help="stack password")
        self.add_argument("--tenant", help="stack tenant")
        self.add_argument("--fqname", help="fqname of the object")
        self.add_argument("--uuid", help="uuid of the object")
        self.add_argument("--obj-type", help="type of the object")

    def parse_args(self, args):
        pargs = super(ArgumentParser, self).parse_args(args)
        pargs = dict(pargs._get_kwargs())
        if os.path.exists(pargs['config']):
            config = ConfigParser.SafeConfigParser()
            config.read(pargs['config'])
            pargs['auth_ip'] = self.read_config_option(config, 'auth',
                               'AUTHN_SERVER', '127.0.0.1')
            pargs['auth_port'] = self.read_config_option(config, 'auth',
                               'AUTHN_PORT', '35357')
            pargs['auth_url_path'] = self.read_config_option(config, 'auth',
                               'AUTHN_URL', '/v2.0/tokens')
            pargs['username'] = pargs['username'] or self.read_config_option(
                               config, 'auth', 'AUTHN_USER', 'admin')
            pargs['password'] = pargs['password'] or self.read_config_option(
                               config, 'auth', 'AUTHN_PASSWORD', 'contrail123')
            pargs['tenant'] = pargs['tenant'] or self.read_config_option(
                               config, 'auth', 'AUTHN_TENANT_NAME', 'admin')
            pargs['config_ip'] = self.read_config_option(config, 'contrail',
                                'CONFIG_IP', '127.0.0.1')
            pargs['config_port'] = self.read_config_option(config, 'contrail',
                                'CONFIG_PORT', '8082')
            pargs['analytics_ip'] = self.read_config_option(config, 'contrail',
                                'ANALYTICS_IP', '')
            pargs['analytics_port'] = self.read_config_option(config, 'contrail',
                                'ANALYTICS_PORT', '8081')
            pargs['control_port'] = self.read_config_option(config, 'contrail',
                                'CONTROL_PORT', '8083')
            pargs['agent_port'] = self.read_config_option(config, 'contrail',
                                'AGENT_PORT', '8085')
            pargs['schema_transformer_port'] = self.read_config_option(config, 'contrail',
                                'SCHEMA_TRANSFORMER_PORT', '8087')
        else:
            raise Exception('Unable to read the ini file %s'%pargs['config'])
        return pargs
