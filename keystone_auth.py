#!/bin/python
import pdb
import logging
import pprint
import json
import re
import logging.handlers
from urlparse import urlparse
import ConfigParser
import os.path

class ContrailKeystoneAuth:
    log = None
    _keystone_con = None
    _authn_server = '127.0.0.1'
    _authn_port = '35357'
    _authn_url = 'v2.0/tokens'
    _authn_user = 'admin'
    _authn_password = 'contrail123'
    _authn_tenant_name = 'admin'
    _authn_config_file = 'auth.ini'

    def __init__(self, **kwargs):
        self._authn_config_file = kwargs.get('auth_config_file', self._authn_config_file)
        if os.path.exists(self._authn_config_file):
            config = ConfigParser.SafeConfigParser()
            config.read([self._authn_config_file])
            auth_config = dict(config.items("auth"))
        else:
            auth_config = dict()
        self._authn_server = auth_config.get('authn_server', self._authn_server)
        self._authn_port = auth_config.get('authn_port', self._authn_port)
        self._authn_url = auth_config.get('authn_url', self._authn_url)
        self._authn_user = auth_config.get('authn_user', self._authn_user)
        self._authn_password = auth_config.get('authn_password', self._authn_password)
        self._authn_tenant_name = auth_config.get('authn_tenant_name', self._authn_tenant_name)

        '''
        self._authn_server = kwargs.get('authn_server', self._authn_server)
        self._authn_port = kwargs.get('authn_port', self._authn_port)
        self._authn_user = kwargs.get('authn_user', self._authn_user)
        self._authn_password = kwargs.get('authn_password', self._authn_password)
        self._authn_tenant_name = kwargs.get('authn_tenant_name', self._authn_tenant_name)
        self._authn_url = kwargs.get('authn_port', self._authn_url)
        '''

        log = self.log
        log =  logging.getLogger("AUTH")
        self.log = log
        log.setLevel('DEBUG')
        logformat = logging.Formatter("%(levelname)s: %(message)s")

        stdout = logging.StreamHandler()
        stdout.setLevel('DEBUG')
        log.addHandler(stdout)
        from contrail_api_con import ContrailApiConnection
        self._keystone_con = ContrailApiConnection()

    def authenticate(self, headers = []):
        url = 'http://%s:%s%s' % (self._authn_server, self._authn_port , self._authn_url)
        authn_headers = ['Content-type: application/json; charset="UTF-8"', 'X-Contrail-Useragent: Debugger']
        headers = headers + authn_headers
        auth_body = {"auth":{"passwordCredentials":{"username": self._authn_user,
                                                    "password": self._authn_password},
                             "tenantName": self._authn_tenant_name }}
        ret_data = self._keystone_con.post(self._authn_url, json.dumps(auth_body),
                                           headers, self._authn_server, self._authn_port)
        return ret_data
        
if __name__ == "__main__":
    import pdb; pdb.set_trace()
    auth = ContrailKeystoneAuth()


