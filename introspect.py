#!/usr/bin/env python
"""Retrieve or Query an object from introspects"""

import json
from logger import logger
import requests
from lxml import etree
from pprint import pprint

class IntrospectUrl(object):
    def __init__(self, url, auth=None):
        self._headers = {'X-AUTH-TOKEN': auth} if auth else None
        self.url = url
        self._load()

    def _load(self):
        self.response = requests.get(self.url, headers=self._headers)
        if not self.response.status_code == 200:
            raise RuntimeError('Retrieve URL (%s) failed with'
                               ' status code (%s)' % (self.url, self.response.status_code))

    def xml_to_etree(self):
        return etree.fromstring(self.response.text)

class EtreeToDict(object):

    """Converts the xml etree to dictionary/list of dictionary."""

    def __init__(self, xpath=None):
        self.xpath = xpath
        self.xml_list = ['policy-rule']

    def _handle_list(self, elems):
        """Handles the list object in etree."""
        a_list = []
        for elem in elems.getchildren():
            rval = self._get_one(elem, a_list)
            if 'element' in rval.keys():
                a_list.append(rval['element'])
            elif 'list' in rval.keys():
                a_list.append(rval['list'])
            else:
                a_list.append(rval)

        if not a_list:
            return None
        return a_list

    def _get_one(self, xp, a_list=None):
        """Recrusively looks for the entry in etree and converts to dictionary.
        Returns a dictionary.
        """
        val = {}

        child = xp.getchildren()
        if not child:
            val.update({xp.tag: xp.text})
            return val

        for elem in child:
            if elem.tag == 'list':
                val.update({xp.tag: self._handle_list(elem)})

            if elem.tag == 'data':
                # Remove CDATA; if present
                text = elem.text.replace("<![CDATA[<", "<").strip("]]>")
                nxml = etree.fromstring(text)
                rval = self._get_one(nxml, a_list)
            else:
                rval = self._get_one(elem, a_list)

            if elem.tag in self.xml_list:
                val.update({xp.tag: self._handle_list(xp)})
            if elem.tag in rval.keys():
                val.update({elem.tag: rval[elem.tag]})
            elif 'SandeshData' in elem.tag:
                val.update({xp.tag: rval})
            else:
                val.update({elem.tag: rval})
        return val

    def get_all_entry(self, etree_obj):
        """All entries in the etree is converted to the dictionary
        Returns the list of dictionary/didctionary.
        """
        if self.xpath is None:
            xps = etree_obj
        else:
            xps = etree_obj.xpath(self.xpath)
            if not xps:
                # sometime ./xpath dosen't work; work around
                # should debug to find the root cause.
                xps = path.xpath(self.xpath.strip('.'))
        if type(xps) is not list:
            return self._get_one(xps)

        val = []
        for xp in xps:
            val.append(self._get_one(xp))
        if len(val) == 1:
            return val[0]
        return val

    def find_entry(self, path, match):
        """Looks for a particular entry in the etree.
        Returns the element looked for/None.
        """
        xp = path.xpath(self.xpath)
        f = filter(lambda x: x.text == match, xp)
        if len(f):
            return f[0].text
        return None

class Introspect(IntrospectUrl, EtreeToDict):
    """ Get Introspect objects as python dictionary or xml
        foo = Introspect.from_ip(ip="10.10.10.1", port=8083, path="/Snh_AgentXmppConnectionStatusReq?")
        or
        foo = Introspect(url="http://10.10.10.1:8083/Snh_AgentXmppConnectionStatusReq?")
    
    """

    def __init__(self, **kwargs):
        self.url = kwargs.get('url', None)
        self.auth = kwargs.get('auth', None)
        self.json = kwargs.get('json', True)
        if self.url is None:
            raise ValueError("Url is required but missing in ARGS")

    @classmethod
    def from_ip(cls, kwargs):
        ip = kwargs.get('ip', None)
        port = kwargs.get('port', None)
        path = kwargs.get('path', None)
        if (ip or port or path) is None:
            raise ValueError('IP (%s) or PORT (%s) or PATH (%s)'
                             ' is required but missing in ARGS' % (ip, port, path))
        url = "http://%s:%s/%s" % (ip, port, path)
        return cls(url=url, **kwargs)

    def get_url_response(self):
        self.url_obj = IntrospectUrl(url=self.url, auth=self.auth)
        self.url_etree_resp = self.url_obj.xml_to_etree()

    def get(self, query=None):
        self.get_url_response()
        return EtreeToDict().get_all_entry(self.url_etree_resp)


class ControllerIntrospectCfg(object):
    @classmethod
    def verify(cls, url, verify_list=None):
        for v in verify_list:
            url_str = url + ('table_name=%s&search_string=%s') % (v['type'], v['fq_name'])
            neighbors_l = cls.matched_adjacencies(url_str)
            for l in v['neighbors']:
                if l not in neighbors_l:
                    print "Controller Error: %s, neighbor not match" % l  
                else:
                    print "Controller Match: %s, link matched" % l

    @classmethod
    def matched_adjacencies(cls, url=None):
        neighbors= []
        if not url:
            return
        iobj = Introspect(url=url) 
        url_dict_resp = iobj.get()
        # Save url_dict_resp 
        neighbors = url_dict_resp['ifmap_db'][0]['neighbors']
        return neighbors

class AgentIntrospectCfg(object):
    @classmethod
    def verify(cls, url, verify_list=None):
        for v in verify_list:
            url_str = url + ('table_name=%s&node_sub_string=%s') % (v['type'], v['fq_name'])
            agent_adj_l = cls.matched_adjacencies(url_str)
            for l in v['neighbors']:
                if l not in agent_adj_l:
                    print "Agent Error: %s, link not matched" % l
                else:
                    print "Agent Match: %s, link matched" % l

    @classmethod
    def matched_adjacencies(cls, url=None):
        adjacencies = []
        if not url:
            return
        iobj = Introspect(url=url) 
        url_dict_resp = iobj.get()
        # Save the url_dict_resp
        table_data = url_dict_resp['table_data'][0].split()
        if 'Adjacencies:' in table_data:
            adj_index = table_data.index('Adjacencies:') + 1
            if adj_index < len(table_data) and len(table_data[adj_index:]) % 2 == 0:
                adjacencies = [k+':'+v for (k, v) in zip(table_data,table_data[1:])[adj_index::2]]
                #adjacencies_tuple = [(k,v) for (k, v) in zip(table_data,table_data[1:])[adj_index::2]]
        return adjacencies

    @classmethod
    def get_adjacencies(cls, url=None, iobj=None, adjacency_type=None, **kwargs):
        adjacency_list = []
        if not url and not iobj:
            ip = kwargs.get('ip', None)
            sandesh_port = kwargs.get('sandesh_port', None)
            uuid = kwargs.get('uuid', None)
            if ip and sandesh_port and uuid:
                url = 'http://%s:%s/Snh_ShowIFMapAgentReq?table_name=&node_sub_string=%s' % \
                      (ip, sandesh_port, uuid)
            else:
                return adjacency_list
            iobj = Introspect(url=url) 
        url_dict_resp = iobj.get()
        # Save the url_dict_resp
        table_data = url_dict_resp['table_data'][0].split()
        if 'Adjacencies:' in table_data:
            adjacencies = []
            adj_index = table_data.index('Adjacencies:') + 1
            if adj_index < len(table_data) and len(table_data[adj_index:]) % 2 == 0:
                #adjacencies = [k+':'+v for (k, v) in zip(table_data,table_data[1:])[adj_index::2]]
                adjacencies = [(k,v,v.split(':')[2]) for (k, v) in zip(table_data,table_data[1:])[adj_index::2]]
            if adjacency_type:
                for adjacency in adjacencies:
                    if adjacency[0] == adjacency_type:
                        adjacency_list.append(adjacency)
            else:
                adjacency_list = adjacencies
        return adjacency_list


verify_list = [
    {'fq_name': 'default-domain:admin:public-vn:public-pool',
     'neighbors': ['virtual-network:default-domain:admin:public-vn',
                   'floating-ip:default-domain:admin:public-vn:public-pool:38ecdc6d-f51a-40b8-b133-46c1ae749cbf',
                   'project:default-domain:admin'],
     'type': 'floating-ip-pool',
     'uuid': 'ebee145e-a5bb-469f-8ca0-7ea962744c59'},
    {'fq_name': 'default-domain:admin:060c2b5f-d43a-4ea5-844d-393819ff36fd',
     'neighbors': ['virtual-machine-interface-routing-instance:attr(default-domain:admin:060c2b5f-d43a-4ea5-844d-393819ff36fd,default-domain:admin:testvn:testvn)',
                   'security-group:default-domain:admin:default',
                   'floating-ip:default-domain:admin:public-vn:public-pool:38ecdc6d-f51a-40b8-b133-46c1ae749cbf',
                   'project:default-domain:admin',
                   'virtual-machine:4c7b468b-69ef-4ea4-a820-69aa06653d2f',
                   'virtual-network:default-domain:admin:testvn',
                   'instance-ip:db161ba2-7036-488d-b9de-fe98a6c49797'],
     'type': 'virtual-machine-interface',
     'uuid': '060c2b5f-d43a-4ea5-844d-393819ff36fd'},
    {'fq_name': 'default-domain:admin:public-vn',
     'neighbors': ['floating-ip-pool:default-domain:admin:public-vn:public-pool',
                   'project:default-domain:admin',
                   'routing-instance:default-domain:admin:public-vn:public-vn',
                   'virtual-network-network-ipam:attr(default-domain:admin:public-vn,default-domain:default-project:default-network-ipam)'],
     'type': 'virtual-network',
     'uuid': 'b19e381f-f2a7-47cf-a037-eb888bd2588c'}
]

base_url = 'http://10.84.17.5'
agent_port = ':8085/'
controller_port = ':8083/'

if __name__ == '__main__':
    ifmap_agent_base_url = base_url + agent_port + 'Snh_ShowIFMapAgentReq?'
    AgentIntrospectCfg.verify(url=ifmap_agent_base_url, verify_list=verify_list)
    ifmap_agent_base_url = base_url + controller_port + 'Snh_IFMapTableShowReq?'
    ControllerIntrospectCfg.verify(url=ifmap_agent_base_url, verify_list=verify_list)
