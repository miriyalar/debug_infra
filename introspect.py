#!/usr/bin/env python
"""Retrieve or Query an object from introspects"""

import requests
import logger
from lxml import etree
from netaddr import IPNetwork, IPAddress

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

class Introspect(object):
    def __init__(self, ip, port, auth=None):
        self._ip = ip
        self._port = port
        self._headers = {'X-AUTH-TOKEN': auth} if auth else None
        self.log = logger.getLogger(logger_name=self.__class__.__name__)

    def _mk_url_str(self, path=''):
        if path.startswith('http:'):
            return path
        return "http://%s:%d/%s" % (self._ip, self._port, path)

    def _load(self, url):
        try:
            resp = requests.get(url, headers=self._headers)
            return resp
        except requests.ConnectionError, e:
            self.log.error("Socket Connection error: %s", str(e))
            raise

    def get(self, path=''):
        if path:
            response = self._load(self._mk_url_str(path))
        if response and response.status_code != 200:
            raise RuntimeError('Retrieve URL (%s) failed with'
                               ' status code (%s)' %(self._mk_url_str(path),
                                                     response.status_code))
        try:
            resp = etree.fromstring(response.text)
            return EtreeToDict().get_all_entry(resp)
        except etree.XMLSyntaxError:
            return json.loads(response.text)

class ControllerIntrospect(Introspect):
    def get_config(self, fq_name_str='', node_type=''):
        url_path = 'Snh_IFMapTableShowReq?table_name=%s&search_string=%s'%(node_type, fq_name_str)
        return self.get(path=url_path)

    def verify(self, verify_list=None):
        for v in verify_list or []:
            neighbors_l = self.matched_adjacencies(node_type=v['type'],
                                                   fq_name_str=v['fq_name'])
            for l in v['neighbors']:
                if l not in neighbors_l:
                    self.log.error("Controller Error: %s, neighbor not match" % l)
                else:
                    self.log.debug("Controller Match: %s, link matched" % l)

    def matched_adjacencies(self, node_type, fq_name_str):
        neighbors= []
        url_dict_resp = self.get_config(node_type=node_type,
                                        fq_name_str=fq_name_str)
        # Save url_dict_resp
        neighbors = url_dict_resp['ifmap_db'][0]['neighbors']
        return neighbors

class AgentIntrospect(Introspect):
    def get_intf_details(self, vmi_id=''):
        url_path = 'Snh_ItfReq?name=&type=&uuid=%s'%(vmi_id)
        return self.get(path=url_path)

    def get_vrf_details(self, vrf_name=''):
        url_path = 'Snh_VrfListReq?x=%s'%vrf_name
        return self.get(path=url_path)

    def get_vm_details(self, vm_id=''):
        url_path = 'Snh_VmListReq?x=%s'%vm_id
        return self.get(path=url_path)

    def get_vn_details(self, vn_id=''):
        url_path = 'Snh_VnListReq?name=&uuid=%s'%vn_id
        return self.get(path=url_path)

    def get_sg_details(self, sg_id=''):
        url_path = 'Snh_SgListReq?name=%s'%sg_id
        return self.get(path=url_path)

    def get_acl_details(self, acl_id=''):
        url_path = 'Snh_AclReq?x=%s'%acl_id
        return self.get(path=url_path)

    def get_config(self, fq_name_str='', node_type=''):
        url_path = 'Snh_ShowIFMapAgentReq?table_name=%s&node_sub_string=%s'% (node_type, fq_name_str)
        return self.get(path=url_path)

    def get_routes(self, vrf_fq_name):
        url_path = 'Snh_PageReq?x=begin:-1,end:-1,table:%s.uc.route.0'%vrf_fq_name
        return self.get(path=url_path)

    def get_flows(self):
        url_path = 'Snh_FetchAllFlowRecords?'
        return self.get(path=url_path)

    def is_prefix_exists(self, vrf_fq_name, prefix, plen=32):
        routes = self.get_routes(vrf_fq_name)
        for route in routes['Inet4UcRouteResp']['route_list']:
            if route['src_ip'] == prefix and route['src_plen'] == str(plen):
                return (True, route)
        return (False, None)

    def is_route_exists(self, vrf_fq_name, address):
        routes = self.get_routes(vrf_fq_name)
        for route in routes['Inet4UcRouteResp']['route_list']:
            if IPAddress(address) in IPNetwork('%s/%s'%(route['src_ip'],
                                                        route['src_plen'])):
               return (True, route)
        return (False, routes)

    def get_matching_flows(self, src_ip=None, dst_ip=None, protocol=None,
                           src_port=None, dst_port=None, src_vn=None,
                           dst_vn=None):
        flows = list()
        for flow in self.get_flows()['flow_list']:
            if src_ip and src_ip != flow['sip']:
                continue
            if dst_ip and dst_ip != flow['dip']:
                continue
            if protocol and protocol != flow['protocol']:
                continue
            if src_port and src_port != flow['src_port']:
                continue
            if dst_port and dst_port != flow['dst_port']:
                continue
            if src_vn and src_vn not in flow['src_vn_match']:
                continue
            if dst_vn and dst_vn not in flow['dst_vn_match']:
                continue
            flows.append(flow)
        return flows

    def get_dropstats(self):
        return self.get('Snh_KDropStatsReq?')

    def verify(self, verify_list=None):
        for v in verify_list or []:
            agent_adj_l = self.matched_adjacencies(node_type=v['type'],
                                                   fq_name_str=v['fq_name'])
            for l in v['neighbors']:
                if l not in agent_adj_l:
                    self.log.error("Agent Error: %s, link not matched" % l)
                else:
                    self.log.debug("Agent Match: %s, link matched" % l)

    def matched_adjacencies(self, node_type, fq_name_str):
        adjacencies = []
        url_dict_resp = self.get_config(node_type=node_type,
                                        fq_name_str=fq_name_str)
        # Save the url_dict_resp
        table_data = url_dict_resp['table_data'][0].split()
        if 'Adjacencies:' in table_data:
            adj_index = table_data.index('Adjacencies:') + 1
            if adj_index < len(table_data) and len(table_data[adj_index:]) % 2 == 0:
                adjacencies = [k+':'+v for (k, v) in zip(table_data,table_data[1:])[adj_index::2]]
                #adjacencies_tuple = [(k,v) for (k, v) in zip(table_data,table_data[1:])[adj_index::2]]
        return adjacencies

    def get_adjacencies(self, adjacency_type=None, uuid=None):
        if not uuid:
            return None
        adjacency_list = []
        url_dict_resp = self.get_config(fq_name_str=uuid)
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
    AgentIntrospect.verify(verify_list=verify_list)
    ifmap_agent_base_url = base_url + controller_port + 'Snh_IFMapTableShowReq?'
    ControllerIntrospect.verify(url=ifmap_agent_base_url, verify_list=verify_list)
