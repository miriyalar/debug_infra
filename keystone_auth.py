#!/bin/python
import pdb
import json
import re
import logger
import ConfigParser
import os.path
from contrail_api_con import ContrailApiConnection

class ContrailKeystoneAuth:
    def __init__(self, auth_ip, auth_port, auth_url_path, admin_username, admin_password, admin_tenant_name):
        self._authn_url = auth_url_path
        self._authn_user = admin_username
        self._authn_password = admin_password
        self._authn_tenant_name = admin_tenant_name
        self.log = logger.getLogger(logger_name='KeystoneAuth')
        self._keystone_con = ContrailApiConnection(ip=auth_ip, port=auth_port)

    def authenticate(self):
        self.log.debug('Authenticating with username: %s,'
                       ' password: %s, tenant: %s'%(self._authn_user,
                       self._authn_password, self._authn_tenant_name))
        authn_headers = {'Content-type': 'application/json; charset="UTF-8"',
                         'X-Contrail-Useragent': 'Debugger'}
        auth_body = {"auth":{"passwordCredentials":{"username": self._authn_user,
                                                    "password": self._authn_password},
                             "tenantName": self._authn_tenant_name }}
        ret_data = self._keystone_con.post_json(self._authn_url,
                                                auth_body)
#                                                authn_headers)
        return ret_data
        
if __name__ == "__main__":
    import pdb; pdb.set_trace()
    auth = ContrailKeystoneAuth()
