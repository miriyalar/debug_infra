#!/bin/python
import pdb
import logging
import json
import re
import logging.handlers
import ConfigParser
import os.path
from contrail_api_con import ContrailApiConnection

class ContrailKeystoneAuth:
    def __init__(self, auth_ip, auth_port, auth_url_path, admin_username, admin_password, admin_tenant_name):
        self._authn_server = auth_ip
        self._authn_port = auth_port
        self._authn_url = auth_url_path
        self._authn_user = admin_username
        self._authn_password = admin_password
        self._authn_tenant_name = admin_tenant_name
#        log = logging.getLogger("AUTH")
#        self.log = log
#        log.setLevel('DEBUG')
#        logformat = logging.Formatter("%(levelname)s: %(message)s")

#        stdout = logging.StreamHandler()
#        stdout.setLevel('DEBUG')
#        log.addHandler(stdout)
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
