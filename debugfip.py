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

class debugVertexFIP(baseVertex):
    dependant_vertexes = ['debugVertexVMI']

    def __init__(self, context=None, **kwargs):
        self.vertex_type = 'floating-ip'
        self.obj_type = 'floating-ip'
        super(debugVertexFIP, self).__init__(context, self.vertex_type, **kwargs)
        if self._is_vertex_type_exists_in_path(self.vertex_type):
            return
        self.logger = logger(logger_name=self.get_class_name()).get_logger()
        obj_type = kwargs.get('obj_type', None)
        if not obj_type:
            obj_type = self.obj_type
        self.floating_ip_address = kwargs.get('floating_ip_address', None)
        fips = self._locate_fip(context=self.context, element = self.element, 
                                obj_type=obj_type, 
                                floating_ip_address=self.floating_ip_address)
        self.process_vertexes(self.vertex_type, fips, self.dependant_vertexes)


    def _locate_fip(self, context, element=None, **kwargs):
        schema_dict = {
                "virtual-machine-interface": {
                        'uuid': 'floating_ip_back_refs',
                }
        }
        #Input_dict
        obj_list = self._locate_obj(schema_dict, element, **kwargs)
        return obj_list

    def _process_local(self, vertex_type, uuid, vertex):
        # Agent
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex_type, vertex)
        self._add_agent_to_context(uuid, agent)
        # Control
        control = {}
        control['oper'] = {}
        self._add_control_to_context(uuid, control)

    def _get_agent_oper_db(self, host_ip, agent_port, vertex_type, vertex):
        oper = {}
        vmi_uuid = None
        adjacency_type='virtual-machine-interface'
        adjacency_list = AgentIntrospectCfg.get_adjacencies(ip=host_ip, sandesh_port=agent_port,
                                                            uuid=vertex[vertex_type]['uuid'],
                                                            adjacency_type=adjacency_type)
        for adjacency in adjacency_list:
            if adjacency[0] == adjacency_type:
                vmi_uuid = adjacency[2]
                break
        if not vmi_uuid:
            self.logger.error("Agent Error, interface is not found in the adjancies of fip %s %s" % \
                              (vertex_type, vertex[vertex_type]['uuid']))
            return oper
        base_url = 'http://%s:%s/' % (host_ip, agent_port)
        intf_str = 'Snh_ItfReq?'
        search_str = ('name=&type=&uuid=%s') % (vmi_uuid)
        url_dict_resp = Introspect(url=base_url + intf_str + search_str).get()
        intf_rec = url_dict_resp['ItfResp']['itf_list'][0]
        oper['interface'] = intf_rec        
        
        match = False
        fip_list = intf_rec['fip_list']
        for fip in fip_list:
            if fip['ip_addr'] == self.floating_ip_address:
                match = True
                fip_vrf = fip['vrf_name']
                fip_address = fip['ip_addr']
                pstr = "FIP address %s is found in the interface rec %s" % \
                       (self.floating_ip_address, intf_rec['name'])
                self.logger.debug(pstr)
                print pstr
                break
        if not match:
            pstr = "fip address %s is not found in the interface rec %s" % \
                   (self.floating_ip_address, intf_rec['name'])
            self.logger.error(pstr)
            print pstr
            return oper

        # Get vrf from 
        vrf_str = 'Snh_VrfListReq?'
        search_str = ('x=%s') % (fip_vrf)
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
                     (ucindex, fip_address)
        routeobj = Introspect(url = base_url + route_str + search_str).get()
        route_rec = routeobj['Inet4UcRouteResp']['route_list'][0]
        oper['route'] = route_rec
        if route_rec:
            nh_list = route_rec['path_list']
            if nh_list:
                print "Agent got nh for %s" % (fip_address)
        else:
            print "Agent Error doesn't have route for %s" % (fip_address)
        return oper


def parse_args(args):
    defaults = {
        'config_ip': '127.0.0.1',
        'config_port': '8082',
        'detail': False,        
    }
    parser = argparse.ArgumentParser(description='Debug utility for FIP',
                                     add_help=True)
    parser.set_defaults(**defaults)
    parser.add_argument('-cip', '--config_ip',
                        help='Config node ip address')
    parser.add_argument('-cport', '--config_port',
                        help='Config node REST API port')
    parser.add_argument('-fip', '--floating_ip_address',
                        help='Floating ip address to debug')
    parser.add_argument('--detail',
                        help='Context detail output to console')
    cliargs = parser.parse_args(args)
    if len(args) == 0:
        parser.print_help()
        sys.exit(2)
    return cliargs

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFIP= debugVertexFIP(config_ip=args.config_ip,
                         config_port=args.config_port,
                         floating_ip_address=args.floating_ip_address)

    context = vFIP.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(context)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json(context)

