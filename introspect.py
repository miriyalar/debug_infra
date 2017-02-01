#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
Retrieve or Query an object from introspects
"""

import requests
import logger
from lxml import etree
from netaddr import IPNetwork, IPAddress
import json
from utils import Utils

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
            if (xp.tag == 'next_batch' or xp.tag == 'next_page' or xp.tag == 'flow_key') \
                and xp.get('link') and xp.text:
                text = 'Snh_%s?x=%s'%(xp.get('link'), xp.text)
            else:
                text = xp.text
            val.update({xp.tag: text})
            return val

        for elem in child:
            # Need to redo with type check for 'list' and skip 'struct'
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
            elif elem.get('type') == "sandesh":
                val.update(rval)
            else:
                val.update({elem.tag: rval})
        return val

    def is_etree_list(self, xobj):
        if type(xobj) is list:
            return True
        child = xobj.getchildren()
        if not child or len(child) < 2:
            return False
        return child[0].tag == child[1].tag

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
        if not self.is_etree_list(xps):
            return self._get_one(xps)

        merged_dict = dict()
        others = dict()
        for xp in xps:
            if xp.tag == xps[0].tag:
                Utils.merge_dict(merged_dict, self._get_one(xp))
            else:
                Utils.merge_dict(others, self._get_one(xp))
        merged_dict.update(others)
        return merged_dict

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

    def _mk_url_str(self, path):
        if path.startswith('http:'):
            return path
        return "http://%s:%s/%s" % (self._ip, self._port, path)

    def _load(self, url):
        try:
            resp = requests.get(url, headers=self._headers)
            return resp
        except requests.ConnectionError, e:
            self.log.error("Socket Connection error: %s", str(e))
            raise

    def get(self, path=None, ref=True):
        response = self._load(self._mk_url_str(path or ''))
        if response and response.status_code != 200:
            raise RuntimeError('Retrieve URL (%s) failed with'
                               ' status code (%s)' %(self._mk_url_str(path or ''),
                                                     response.status_code))
        try:
            resp = etree.fromstring(response.text)
            etodict = EtreeToDict().get_all_entry(resp)
            if etodict and ref:
               etodict['ref'] = self._mk_url_str(path or '')
            return etodict
        except etree.XMLSyntaxError:
            try:
                return json.loads(response.text)
            except ValueError:
                return response.text

    def is_service_up(self):
        try:
            response = self.get()
            return True
        except requests.ConnectionError:
            return False

class SchemaIntrospect(Introspect):
    def get_object(self, object_type, uuid=None, fq_name=None):
        url_path = 'Snh_StObjectReq?object_type=%s&object_id_or_fq_name=%s'%(
                    object_type, (uuid or fq_name or ''))
        response = self.get(url_path)
        if not response or not response.get('objects'):
            return []
        return response['objects']

    def get_service_chains(self, sc_name=None, vn_list=None):
        response = self.get_object('service_chain', sc_name or '')
        if sc_name:
            return response
        service_chains = list()
        for service_chain in response:
            prop = {p['property_name']:p['property'] for p in service_chain['properties']}
            if vn_list:
                left_vn = prop['left_network']
                right_vn = prop['right_network']
                if set(vn_list) - set((left_vn, right_vn)):
                    continue
                service_chains.append(service_chain)
        return service_chains

    def get_service_instances(self, si_uuid=None, si_fqname=None):
        return self.get_object('service_instance', si_uuid, si_fqname)

    def get_virtual_networks(self, vn_uuid=None, vn_fqname=None):
        return self.get_object('virtual_network', vn_uuid, vn_fqname)

    def get_vrfs_of_vn(self, vn_uuid=None, vn_fqname=None, sc_uuid=None, si_name=None):
        vn_obj = self.get_virtual_networks(vn_uuid, vn_fqname)[0]
        refs = {p['object_type']:p['object_fq_name']
                for p in vn_obj['obj_refs']}
        match = vn_obj['object_fq_name']
        ris = list()
        for ri in refs['routing_instance']:
            if (sc_uuid and 'service-'+sc_uuid not in ri) or \
                (si_name and not ri.endswith(si_name.replace(':', '_'))):
                continue
            ris.append(ri)
        return ris

class ControllerIntrospect(Introspect):
    def get(self, path=None, ref=None):
        response = super(ControllerIntrospect, self).get(path)
        if response and response.get('next_batch'):
            Utils.merge_dict(response, self.get(response['next_batch']))
        return response

    def get_config(self, fq_name_str=None, node_type=None):
        url_path = 'Snh_IFMapTableShowReq?table_name=%s&search_string=%s'%(
                    node_type or '', fq_name_str or '')
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

    def get_routes(self, vrf_fq_name, url_path):
        return self.get(path=url_path)

    def is_route_exists(self, vrf_fq_name, address, rt_type):
        if rt_type == 'inet':
            rt_name = 'inet'
        elif rt_type == 'inet6':
            rt_name = 'inet6'
        elif ((rt_type == 'bridge') or (rt_type == 'evpn')):
            rt_name = 'evpn'
        else:
            rt_name = None
            routes = None
            return(False, routes)

        if (rt_type == 'evpn'):
            prefix = address.split(',')
        url_path = 'Snh_ShowRouteReq?x=%s.%s.0'%(vrf_fq_name, rt_name)
        routes = self.get_routes(vrf_fq_name, url_path)
        route_list = list()
        for route in routes['tables'][0]['routes']:
            if ((rt_type == 'inet') or (rt_type == 'inet6')):
                if IPAddress(address) in IPNetwork(route['prefix']):
                    route_list.append(route)
            if (rt_type == 'bridge'):
                if address in route['prefix']:
                    route_list.append(route)
            if (rt_type == 'evpn'):
                if ((prefix[0] in route['prefix']) and (prefix[1] in route['prefix'])):
                    route_list.append(route)
        if route_list:
            return (True, route_list)
        return (False, routes)

    def get_bgpneighbor_list(self):
        url_path = 'Snh_BgpNeighborReq'
        return self.get(path=url_path)


class AgentIntrospect(Introspect):
    def get(self, path=None, ref=None):
        response = super(AgentIntrospect, self).get(path)
        # Handle Pagination
        try:
            # Format 1 - Check for Pagination section
            if response and response.get('req') and \
               response['req'].get('PageReqData'):
                next_page = response['req']['PageReqData']['next_page']
                if next_page:
                    Utils.merge_dict(response, self.get(next_page))
            # Format 2 - Check for multiple flow pages
            elif response and response.get('flow_key'):
                next_page = response['flow_key']
                if next_page and '0.0.0.0-0.0.0.0' not in next_page:
                    Utils.merge_dict(response, self.get(next_page))
        except:
            pass
        return response

    def get_intf_details(self, vmi_id=None):
        url_path = 'Snh_ItfReq?name=&type=&uuid=%s'%(vmi_id or '')
        return self.get(path=url_path)

    def get_vrf_details(self, vrf_name=None):
        url_path = 'Snh_VrfListReq?x=%s'%(vrf_name or '')
        return self.get(path=url_path)

    def get_vm_details(self, vm_id=None):
        url_path = 'Snh_VmListReq?x=%s'%(vm_id or '')
        return self.get(path=url_path)

    def get_vn_details(self, vn_id=None):
        url_path = 'Snh_VnListReq?name=&uuid=%s'%(vn_id or '')
        return self.get(path=url_path)

    def get_sg_details(self, sg_id=None):
        url_path = 'Snh_SgListReq?name=%s'%(sg_id or '')
        return self.get(path=url_path)

    def get_acl_details(self, acl_id=None):
        url_path = 'Snh_AclReq?x=%s'%(acl_id or '')
        return self.get(path=url_path)

    def get_config(self, fq_name_str=None, node_type=None):
        url_path = 'Snh_ShowIFMapAgentReq?table_name=%s&node_sub_string=%s'%(
                    node_type or '', fq_name_str or '')
        return self.get(path=url_path)

    def get_routes(self, vrf_fq_name, url_path):
        return self.get(path=url_path)

    def get_kroutes(self, vrf_id=None, vrf_fq_name=None, url_path=None):
        if not vrf_id and vrf_fq_name:
            vrf_id = self.get_vrf_id(vrf_fq_name)
        if not vrf_id:
            self.log.debug('Unable to find vrf_id %s fq_name %s on node %s'%(
                            vrf_id, vrf_fq_name, self._ip))
            return []
        return self.get(path=url_path)

    def get_flows(self):
        url_path = 'Snh_FetchAllFlowRecords?'
        return self.get(path=url_path)

    def get_kflows(self, flow_index=None):
        url_path = 'Snh_KFlowReq?flow_idx=%s'%(flow_index or '')
        return self.get(path=url_path)

    def get_nh(self, nh_index=None):
        url_path = 'Snh_NhListReq?type=&nh_index=%s'%(nh_index or '')
        return self.get(path=url_path)

    def get_knh(self, nh_index=None):
        nh_list = list()
        url_path = 'Snh_KNHReq?nh_id=%s'%(nh_index or '')
        response = self.get(path=url_path)
        if not response or not response.get('nh_list'):
            return []
        nh_list.extend(response['nh_list'])
        if nh_index:
            for nh in response['nh_list']:
                if nh['type'].upper() == 'COMPOSITE':
                    for index in nh['component_nh']:
                        nh_list.extend(self.get_knh(index['nh_id']))
        return nh_list

    def get_vrf_fqname(self, vrf_index):
        url_path = 'Snh_Inet4UcRouteReq?vrf_index=%s'%vrf_index
        routes = self.get(path=url_path)
        if not routes or not routes.get('route_list'):
            self.log.debug('Unable to find vrf_name of vrf_id %s'%vrf_index)
        return routes['route_list'][0]['src_vrf']

    def get_vrf_id(self, vrf_fqname):
        if not vrf_fqname:
            return None
        url_path = 'Snh_VrfListReq?name=%s'%vrf_fqname
        response = self.get(url_path)
        if not response['vrf_list']:
            return None
        return [x['ucindex'] for x in response['vrf_list'] if x['name'] == vrf_fqname][0]

    def is_prefix_exists(self, vrf_fq_name, prefix, plen=32):
        (exists, routes) = self.is_route_exists(vrf_fq_name, prefix, rt_type='inet')
        if exists:
            for route in routes:
                if route['src_ip'] == prefix and route['src_plen'] == str(plen):
                    return (True, route)
        return (False, None)

    def is_route_exists(self, vrf_fq_name, address, rt_type, lpm=False):
        if rt_type == 'inet':
            rt_name = 'uc.route'
        elif rt_type == 'inet6':
            rt_name = 'uc.route6'
        elif rt_type == 'bridge':
            rt_name = 'l2.route'
        elif rt_type == 'evpn':
            rt_name = 'evpn.route'
        else:
            rt_name = None
            routes = None
            return (False, routes)

        if (rt_type == 'evpn'):
            prefix = address.split(',')

        url_path = 'Snh_PageReq?x=begin:-1,end:-1,table:%s.%s.0'%(vrf_fq_name, rt_name)
        routes = self.get_routes(vrf_fq_name, url_path)
        if not routes or not routes.get('route_list'):
            self.log.debug('No route exists on vrf %s in %s'%(vrf_fq_name, self._ip))
            return (False, [])
        route_list = list()
        for route in routes['route_list']:
            if ((rt_type == 'inet') or (rt_type == 'inet6')):
                if IPAddress(address) in IPNetwork('%s/%s'%(route['src_ip'],
                                                        route['src_plen'])):
                    route_list.append(route)
            if (rt_type == 'bridge'):
                if address in route['mac']:
                    route_list.append(route)
            if (rt_type == 'evpn'):
                if ((prefix[0] in route['mac']) and (prefix[1] in route['mac'])):
                    route_list.append(route)
        if route_list:
            return (True, route_list[-1:] if lpm else route_list)
        self.log.debug('route for %s doesnt exist on vrf %s in %s'%(address, vrf_fq_name, self._ip))
        return (False, routes)

    def is_kroute_exists(self, address, rt_type, vrf_id=None, vrf_fq_name=None, lpm=False):
        if rt_type == 'inet':
            family_name = 'inet'
        elif rt_type == 'inet6':
            family_name = 'inet6'
        elif ((rt_type == 'bridge') or (rt_type == 'evpn')):
            family_name = 'bridge'
        else:
            family_name = None
        if (rt_type == 'evpn'):
            prefix = address.split(',')
        if not vrf_id and vrf_fq_name:
            vrf_id = self.get_vrf_id(vrf_fq_name)
        url_path = 'Snh_KRouteReq?vrf_id=%s&family=%s'%(vrf_id, family_name)
        routes = self.get_kroutes(vrf_id=vrf_id, vrf_fq_name=vrf_fq_name, url_path=url_path)
        if not routes or not routes.get('rt_list'):
            self.log.debug('No route exists on vrf %s in %s'%(vrf_id, self._ip))
            return (False, [])
        route_list = list()
        for route in routes['rt_list']:
            if ((rt_type == 'inet') or (rt_type == 'inet6')):
                if IPAddress(address) in IPNetwork('%s/%s'%(route['prefix'],
                                                        route['prefix_len'])):
                    route_list.append(route)
            if (rt_type == 'bridge'):
                if address in route['rtr_mac']:
                    route_list.append(route)
            if (rt_type == 'evpn'):
                if prefix[0] in route['rtr_mac']:
                    route_list.append(route)
        if route_list:
            return (True, route_list[-1:] if lpm else route_list)
        self.log.debug('route for %s doesnt exist on vrf %s in %s'%(address, vrf_id, self._ip))
        return (False, routes)

    def get_matching_flows(self, src_ip=None, dst_ip=None, protocol=None,
                           src_port=None, dst_port=None, src_vn=None,
                           dst_vn=None, src_nip=None, dst_nip=None,
                           src_nvn=None, dst_nvn=None,
                           src_vrf_id=None, dest_vrf_id=None):
        matched_flows = list()
        flows = self.get_flows()
        if not flows:
            return matched_flows
        natip_set = set(list(src_nip or []) + list(dst_nip or []))
        ip_set = set([src_ip, dst_ip] + list(natip_set))
        vn_set = set([src_vn, dst_vn, src_nvn, dst_nvn])
        vrf_set = set([src_vrf_id, dest_vrf_id])
        ip_set.discard(None); ip_set.discard('')
        vn_set.discard(None); vn_set.discard('')
        vrf_set.discard(None); vrf_set.discard('')
        for flow in flows['flow_list'] or []:
            if src_ip and dst_ip:
                if ip_set and flow['sip'] not in ip_set:
                    continue
                if ip_set and flow['dip'] not in ip_set:
                    continue
            else:
                if ip_set and not (set(flow['sip'], flow['dip']) & ip_set):
                    continue
            if protocol and protocol != flow['protocol']:
                continue
            if src_port and src_port != flow['src_port']:
                continue
            if dst_port and dst_port != flow['dst_port']:
                continue
            if vn_set and flow['src_vn_match'] not in vn_set:
                continue
            if vn_set and flow['dst_vn_match'] not in vn_set:
                continue
            if vrf_set and flow['vrf'] not in vrf_set:
                continue
            if vrf_set and flow['dest_vrf'] not in vrf_set:
                continue
            if natip_set and not natip_set & set([flow['sip'], flow['dip']]):
                self.log.warn('We expect the flow to be natted to '
                              '%s where as it isnt'%natip_set)
            matched_flows.append(flow)
        return matched_flows

    def get_matching_kflows(self, src_ip=None, dst_ip=None, protocol=None,
                            src_port=None, dst_port=None, src_nip=None,
                            dst_nip=None, src_vrf_id=None, dest_vrf_id=None,
                            flow_ids=None):
        matched_flows = list()
        if flow_ids:
            for flow_id in list(set(flow_ids)):
                flow = self.get_kflows(flow_id)
                if not flow or not flow.get('flow_list'):
                    self.log.debug('Flow index %s not found in kernel of %s'%(
                                   flow_id, self._ip))
                    continue
                matched_flows.extend(flow['flow_list'])
            return matched_flows
        flows = self.get_kflows()
        if not flows:
            return matched_flows
        ip_set = set([src_ip, dst_ip] + list(src_nip or []) + list(dst_nip or []))
        vrf_set = set([src_vrf_id, dest_vrf_id])
        ip_set.discard(None); ip_set.discard('')
        vrf_set.discard(None); vrf_set.discard('')
        for flow in flows['flow_list'] or []:
            if ip_set and flow['sip'] not in ip_set:
                continue
            if ip_set and flow['dip'] not in ip_set:
                continue
            if protocol and protocol != flow['proto']:
                continue
            if src_port and src_port != flow['sport']:
                continue
            if dst_port and dst_port != flow['dport']:
                continue
            if vrf_set and flow['vrf_id'] not in vrf_set:
                continue
            if vrf_set and flow['d_vrf_id'] not in vrf_set:
                continue
            matched_flows.append(flow)
        return matched_flows

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
        if not url_dict_resp or not url_dict_resp.get('table_data'):
            return []
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

    def get_bgpasas_details(self):
        url_path = 'Snh_BgpAsAServiceSandeshReq'
        return self.get(path=url_path)


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
