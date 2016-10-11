#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
Config node connection with authentication
"""

import pdb
import re
import pprint
import json
import logger
from utils import Utils
from contrail_api_con_exception import ContrailApiConnectionException
from contrail_con_enum import ContrailConError
from requests.exceptions import ConnectionError
import requests

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO


class ContrailApiConnection:
    def  __init__(self, ip = None, port = None, headers = None):
        self.log =  logger.getLogger(logger_name=self.__class__.__name__)
        self.ip = ip
        self.port = port
	if (ip == None or port == None):
            return

        self.url = "http://%s:%s" % (ip, port)
        self._hdr = headers or {}

    def get_encoded_response(self, headers, response):
        # Figure out what encoding was sent with the response, if any.
        # Check against lowercased header name.
        encoding = None
        if 'content-type' in headers:
            content_type = headers['content-type'].lower()
            match = re.search('charset=(\S+)', content_type)
            if match:
                encoding = match.group(1)
        if encoding is None:
            # Default encoding for HTML is iso-8859-1.
            # Other content types may have different default encoding,
            # or in case of binary data, may have no encoding at all.
            encoding = 'ISO-8859-1'

        response.encoding = encoding
        return response.text

    def get(self, url_path, ref=True):
        url = ("%s/%s") % (self.url, url_path)
        self.log.debug("url = %s" %url)
        try:
            response = requests.get(url, headers=self._hdr)
        except ConnectionError as e:
            self.log.critical(("Error connecting to the server %s:%s") % (self.ip, self.port))
	if response.status_code == 200:
            resp = self.get_encoded_response(self._hdr, response)
	elif response.status_code == 401:
            #auth to keystone server
            raise ContrailApiConnectionException("Authentication Required",
						 ContrailConError.AUTH_FAILURE)
        else:
            pstr = "http resp code:%s, http headers:%s, http resp buffer:%s" % \
                   (response.status_code, str(self._hdr), str(response.text))
            raise ContrailApiConnectionException(pstr)

        json_data = json.loads(resp)
        tdict = Utils.convert_unicode(json_data)
        if tdict and ref:
            tdict['ref'] = url
        return tdict 

    def post(self, url_path, post_data, headers=None):
        pstr = ("Making a post request to %s with %s") % (url_path, post_data)
        self.log.debug(pstr)
        url = "%s/%s" %(self.url, url_path)
        hdr = dict(self._hdr)
        hdr.update(headers or {})
        try:
            response = requests.post(url, data=post_data, headers=hdr)
        except ConnectionError as e:
            self.log.critical(("Error connecting to the server %s:%s") % (self.ip, self.port))
        if response.status_code == 200:
            resp = self.get_encoded_response(hdr, response)
        elif response.status_code == 401:
            #auth to keystone server failed
            raise ContrailApiConnectionException("Authentication Required",
                                                 ContrailConError.AUTH_FAILURE)
        else:
            pstr = "http resp code:%s, http headers:%s, http resp buffer:%s" % \
                   (response.status_code, hdr, str(response.text))
            raise ContrailApiConnectionException(pstr)

        json_data = json.loads(resp)
        return Utils.convert_unicode(json_data)

    def post_json(self, url_path, post_data, headers=None):
        headers = headers or {}
        headers.update({'Content-type': 'application/json; charset="UTF-8"'})
        data = json.dumps(post_data)
        return self.post(url_path, data, headers)

#End of ContrailApiConnection

if __name__ == "__main__":
    #con = ContrailApiConnection(ip='127.0.0.1', port=8095, username = 'admin', password = 'contrail123')
    con = ContrailApiConnection(ip='10.84.17.5', port=8082, username = 'admin', password = 'contrail123')
    pdb.set_trace()
    domain_given_uuid = con.post_json("id-to-fqname", {"uuid": "d140a50f-39b7-42cb-9db1-7ed6c6a8a6dc"})

    domains = con.get("domains")
    virtual_networks = con.get("virtual-networks")
#    domain_given_uuid = con.post("id-to-fqname", {"uuid": "d140a50f-39b7-42cb-9db1-7ed6c6a8a6dc"})

