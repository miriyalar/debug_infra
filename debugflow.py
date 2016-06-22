'''
Take context as argument, in addition to regular input of 4-tuple
Create a uuid, fq_name for a flow and stick in the vertex
base flow verter class?
should we create a singleton object for context and use it at baseVertex and baseFlowVertex

'''

import sys
import argparse
from logger import logger
from contrail_api import ContrailApi
from introspect import Introspect
from introspect import AgentIntrospectCfg
from contrail_utils import ContrailUtils
from collections import OrderedDict
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
from debugip import debugVertexIP
from debugfip import debugVertexFIP

class debugVertexFlow(object):
    vertex_type = 'flow'
    def __init__(self, **kwargs):
        self.logger = logger(logger_name=self.__class__.__name__).get_logger()
        self.source_ip = kwargs.pop('source_ip', None)
        self.dest_ip = kwargs.pop('dest_ip', None)
        self.source_vn = kwargs.pop('source_vn', None)
        self.dest_vn = kwargs.pop('dest_vn', None)
        self.protocol = kwargs.pop('protocol', None)
        self.source_port = kwargs.pop('source_port', None)
        self.dest_port = kwargs.pop('dest_port', None)
        self.srcip_vertex = debugVertexIP(instance_ip_address=self.source_ip, **kwargs)
        srcip_uuid = self.srcip_vertex.get_vertexes()[0]['uuid']
        src_vrouter = self.srcip_vertex.get_vrouters()[0]
        src_agent_oper = self._get_agent_oper_db(src_vrouter['hostname'] + ':src',
                                                 src_vrouter['ip_address'], src_vrouter['sandesh_http_port'],
                                                 srcip_uuid, self.source_ip)
        self.destip_vertex = debugVertexIP(instance_ip_address=self.dest_ip,
                                           context=self.srcip_vertex.get_context(), **kwargs)
        destip_uuid = self.destip_vertex.get_vertexes()[0]['uuid']
        dest_vrouter = self.destip_vertex.get_vrouters()[0]
        dest_agent_oper = self._get_agent_oper_db(dest_vrouter['hostname'] + ':dest',
                                                  dest_vrouter['ip_address'], dest_vrouter['sandesh_http_port'],
                                                  destip_uuid, self.dest_ip)
        import pdb; pdb.set_trace()
        self.check_routes()


    def check_routes(self):
        pass

    def _get_agent_oper_db(self, identifier, host_ip, agent_port, uuid, instance_ip):
        oper = {}
        oper[identifier] = {}
        host_oper = oper[identifier]
        error = False
        adjacency_type='virtual-machine-interface'
        adjacency_list = AgentIntrospectCfg.get_adjacencies(ip=host_ip, sandesh_port=agent_port,
                                                            uuid=uuid,
                                                            adjacency_type=adjacency_type)
        for adjacency in adjacency_list:
            if adjacency[0] == adjacency_type:
                vmi_uuid = adjacency[2]
                break
        if not vmi_uuid:
            self.logger.error("Agent Error, interface is not found in the adjancies of ip %s %s" % \
                              (instance_ip, uuid))
            return oper
        base_url = 'http://%s:%s/' % (host_ip, agent_port)
        intf_str = 'Snh_ItfReq?'
        search_str = ('name=&type=&uuid=%s') % (vmi_uuid)
        url_dict_resp = Introspect(url=base_url + intf_str + search_str).get()
        intf_rec = url_dict_resp['ItfResp']['itf_list'][0]
        host_oper['interface'] = intf_rec

        ip_address = host_oper['interface']['ip_addr']
        if ip_address == instance_ip:
            pstr = "IP address %s is found in the interface rec %s" % \
                   (instance_ip, intf_rec['name'])
            self.logger.debug(pstr)
            print pstr
        else:
            pstr = "IP address %s is NOT found in the interface rec %s" % \
                   (instance_ip, intf_rec['name'])
            self.logger.error(pstr)
            print pstr
            return oper

        # Get vrf from
        vrf = intf_rec['vrf_name']
        vrf_str = 'Snh_VrfListReq?'
        search_str = ('x=%s') % (vrf)
        ivrfobj = Introspect(url= base_url + vrf_str + search_str)
        vrfobj = ivrfobj.get()
        if vrfobj['VrfListResp']['vrf_list']:
            ucindex = vrfobj['VrfListResp']['vrf_list'][0]['ucindex']
        else:
            self.logger.error("Agent Error, fip vrf not found")
            return oper

        # Get routing entry
        route_str = 'Snh_Inet4UcRouteReq?'
        search_str = ('vrf_index=%s&src_ip=%s&prefix_len=32') % \
                     (ucindex, ip_address)
        routeobj = Introspect(url = base_url + route_str + search_str).get()
        route_rec = routeobj['Inet4UcRouteResp']['route_list'][0]
        host_oper['route'] = route_rec
        if route_rec:
            nh_list = route_rec['path_list']
            if nh_list:
                print "Agent got nh for %s" % (ip_address)
        else:
            print "Agent Error doesn't have route for %s" % (ip_address)
        return oper



def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Flow', add_help=True)
    parser.add_argument('--source_ip', help='Source IP of the flow', required=True)
    parser.add_argument('--dest_ip', help='Destination IP of the flow', required=True)
    parser.add_argument('--source_vn', help='VN of the source IP')
    parser.add_argument('--dest_vn', help='VN of the destination IP')
    parser.add_argument('--protocol', help='L3 Protocol of the flow')
    parser.add_argument('--source_port', help='Source Port of the flow')
    parser.add_argument('--dest_port', help='Destination Port of the flow')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFlow= debugVertexFlow(**args)

    context = vFlow.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(context)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json(context)

