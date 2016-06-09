#!/bin/python
import pdb
import pycurl
import logging
import re
import pprint
import json
import logging.handlers
from utils import Utils
from contrail_api_con_exception import ContrailApiConnectionException
from contrail_con_enum import ContrailConError

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO


class ContrailApiConnection:
    #Make this a private variable
    _con = None
    ip =''
    port = ''
    username = ''
    password = ''
    headers = {}
    resp_buffer = None
    log = None

    def _set_auth(self, con):
        if self.username != None and self.password != None: 
            auth_str = '%s:%s' % (self.username, self.password)
            con.setopt(con.USERPWD, auth_str)
            #self.log.info('Authentication is set!')
        #else:
            #self.log.info('Authentication not set!')

    def header_function(self, header_line):
        # HTTP standard specifies that headers are encoded in iso-8859-1.
        # On Python 2, decoding step can be skipped.
        # On Python 3, decoding step is required.
        header_line = header_line.decode('iso-8859-1')

        # Header lines include the first status line (HTTP/1.x ...).
        # We are going to ignore all lines that don't have a colon in them.
        # This will botch headers that are split on multiple lines...
        if ':' not in header_line:
            return

        # Break the header line into header name and value.
        name, value = header_line.split(':', 1)

        # Remove whitespace that may be present.
        # Header lines include the trailing newline, and there may be whitespace
        # around the colon.
        name = name.strip()
        value = value.strip()

        # Header names are case insensitive.
        # Lowercase name here.
        name = name.lower()

        # Now we can actually record the header name and value.
        self.headers[name] = value

    def  __init__(self, ip = None, port = None, username = None, password = None, headers = []):
        #get logger object
        log =  logging.getLogger("debug")
        self.log = log
        log.setLevel('ERROR')
        logformat = logging.Formatter("%(levelname)s: %(message)s")
#        fh = logging.FileHandler('debug.log')
#        fh.setLevel(logging.DEBUG)

        stdout = logging.StreamHandler()
        stdout.setLevel('DEBUG')
    #    fh.setFormatter(logformat)
        log.addHandler(stdout)


        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        #log.info(("Intializing with values %s:%s:%s:%s") % (ip, port, username, password))
        _con = pycurl.Curl()
        self._con = _con
        if not _con:
            log.critical("Error creating the python object")
	if (ip == None or port == None):
            return
		
        url = ("http://%s:%s") % (ip, port)
        _con.setopt(_con.URL, url)
        # Follow redirect.
        _con.setopt(_con.FOLLOWLOCATION, True)
        self.resp_buffer = BytesIO()
        _con.setopt(_con.WRITEFUNCTION, self.resp_buffer.write)
        # Set our header function.
        _con.setopt(_con.HEADERFUNCTION, self.header_function)
        self._hdr = headers
        _con.setopt(pycurl.HTTPHEADER, headers)
        self._set_auth(_con)
        try:
            _con.perform()
        except pycurl.error as e:
            log.critical(("Error connecting to the server %s:%s") % (ip, port))

	resp_code = self._get_resp_code(_con)
	if resp_code == 200:
           self._con = _con
	elif resp_code == 401:
           #TODO Raise an exception		
           #auth to keystone server
           raise ContrailApiConnectionException("Authentication Requires",
						 ContrailConError.AUTH_FAILURE)		



    def get_encoded_response(self, headers, resp_buffer):
        # Figure out what encoding was sent with the response, if any.
        # Check against lowercased header name.
        
        encoding = None
        if 'content-type' in headers:
            content_type = headers['content-type'].lower()
            match = re.search('charset=(\S+)', content_type)
            if match:
                encoding = match.group(1)
                #print('Decoding using %s' % encoding)
        if encoding is None:
            # Default encoding for HTML is iso-8859-1.
            # Other content types may have different default encoding,
            # or in case of binary data, may have no encoding at all.
            encoding = 'iso-8859-1'
            #print('Assuming encoding is %s' % encoding)

        body = resp_buffer.getvalue()
        # Decode using the encoding we figured out.
        return (body)

    def _register_callbacks(self):
        _con = self._con
        # Follow redirect.
        _con.setopt(_con.FOLLOWLOCATION, True)
        self.resp_buffer = BytesIO()
        _con.setopt(_con.WRITEFUNCTION, self.resp_buffer.write)
        # Set our header function.
        _con.setopt(_con.HEADERFUNCTION, self.header_function)

    def _get_resp_code(self, curl):
        if curl == None:
            return None
        return curl.getinfo(pycurl.HTTP_CODE)


    def get(self, http_obj):

        url = ("http://%s:%s/%s") % (self.ip, self.port, http_obj)
        _con = self._con
        self.log.debug(("url = %s") % (url))
        _con.setopt(_con.URL, url)
        _con.setopt(pycurl.POST, 0)
#        self._register_callbacks(self.resp_buffer, self.header_function)
        # Follow redirect.
        _con.setopt(_con.FOLLOWLOCATION, True)
 
        self.resp_buffer = BytesIO()
        #_con.setopt(pycurl.VERBOSE, 1)
        _con.setopt(_con.WRITEFUNCTION, self.resp_buffer.write)
        # Set our header function.
#        _con.setopt(_con.HEADERFUNCTION, self.header_function)

        try:
            _con.perform()
        except pycurl.error as e:
            self.log.critical(("Error connecting to the server %s:%s") % (self.ip, self.port))
	resp_code = self._get_resp_code(_con)
	resp = None
	if resp_code == 200:
            resp = self.get_encoded_response(self.headers, self.resp_buffer) 
	elif resp_code == 401:
            #auth to keystone server
            raise ContrailApiConnectionException("Authentication Requires",
						 ContrailConError.AUTH_FAILURE)
        else:
            pstr = "http resp code:%s, http headers:%s, http resp buffer:%s" % \
                   (resp_code, str(self.headers), str(self.resp_buffer.getvalue()))
            raise ContrailApiConnectionException(pstr)

        #self.log.debug(("Headers = %s") % (self.headers))
        #self.log.debug(("Body = %s") % (resp))
        json_data = json.loads(resp)
        return Utils.convert_unicode(json_data)


    def post(self, http_object, post_data, headers = [], ip = None, port = None):
        #TODO
        pstr = ("Making a post request to %s with %s") % (http_object, post_data)
        self.log.debug(pstr)
        #print pstr
        
        if ip == None:
            ip = self.ip
        if port == None:
            port = self.port
        url = ("http://%s:%s/%s") % (ip, port, http_object)
        _con = self._con
        #_con.setopt(pycurl.VERBOSE, 1)
        _con.setopt(_con.URL, url)
        if headers:
            if hasattr(self, '_hdr'):
                _con.setopt(pycurl.HTTPHEADER, self._hdr + headers)
            else:
                _con.setopt(pycurl.HTTPHEADER, headers)
        _con.setopt(pycurl.POST, 1)
        _con.setopt(pycurl.POSTFIELDS, post_data)
#        self._register_callbacks(self.resp_buffer, self.header_function)
        # Follow redirect.
        _con.setopt(_con.FOLLOWLOCATION, True)
        self.resp_buffer = BytesIO()
        _con.setopt(_con.WRITEFUNCTION, self.resp_buffer.write)
        #_con.setopt(pycurl.VERBOSE, 1)
        try:
            _con.perform()
        except pycurl.error as e:
            self.log.critical(("Error connecting to the server %s:%s") % (self.ip, self.port))
        resp = self.get_encoded_response(self.headers, self.resp_buffer) 

        #self.log.debug(("Headers = %s") % (self.headers))
        #self.log.debug(("Body = %s") % (resp))
        json_data = json.loads(resp)
        return Utils.convert_unicode(json_data)

    def post_json(self, http_object, post_data, headers = ["Content-Type: application/json"]): 
        data = json.dumps(post_data)
        return self.post(http_object, data, headers) 

#End of ContrailApiConnection

if __name__ == "__main__":
    #con = ContrailApiConnection(ip='127.0.0.1', port=8095, username = 'admin', password = 'contrail123') 
    con = ContrailApiConnection(ip='10.84.17.5', port=8082, username = 'admin', password = 'contrail123')
    pdb.set_trace() 
    domain_given_uuid = con.post_json("id-to-fqname", {"uuid": "d140a50f-39b7-42cb-9db1-7ed6c6a8a6dc"})

    domains = con.get("domains") 
    virtual_networks = con.get("virtual-networks") 
#    domain_given_uuid = con.post("id-to-fqname", {"uuid": "d140a50f-39b7-42cb-9db1-7ed6c6a8a6dc"})

