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

class debugVertexVN(baseVertex):
    dependant_vertexes = ['debugVertexVMI']
    vertex_type = 'virtual-network'

    def process_self(self, vertex_type, uuid, vertex):
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex_type, vertex)
        self._add_agent_to_context(uuid, agent)
        control = {}
        control['oper'] = {}
        self._add_control_to_context(uuid, control)        

    def _get_agent_oper_db(self, host_ip, agent_port, vertex_type, vertex):
        error = False
        base_url = 'http://%s:%s/' % (host_ip, agent_port)
        vn_uuid = vertex[vertex_type]['uuid']
        search_str = 'Snh_VnListReq?name=&uuid=%s' % (vn_uuid)
        oper = {}
        url_dict_resp = Introspect(url=base_url + search_str).get()
        if len(url_dict_resp['VnListResp']['vn_list']) == 1:
            vn_rec = url_dict_resp['VnListResp']['vn_list'][0]
            oper[vertex_type] = vn_rec
        else:
            error = True
            pstr = "Got more vn records, supposed to have one for uuid %d" % (vn_uuid)
            self.logger.error(pstr)
            print pstr
        pstr = "Agent Verified virtual network %s %s" % (vn_uuid, 'with errors' if error else '')
        self.logger.debug(pstr)
        print pstr
        return oper
                
    def get_schema(self, **kwargs):
        #VN Name, VN UUID, VMI UUID
        schema_dict = {
                "virtual-machine": {
                    "uuid": 'virtual_machine_interface_back_refs.virtual_network_refs'
                },
                "virtual-machine-interface": {
                    "uuid": 'virtual_network_refs'
                }
        }
        return schema_dict


def parse_args(args):
    defaults = {
        'config_ip': '127.0.0.1',
        'config_port': '8082',
        'detail': False,        
    }
    parser = argparse.ArgumentParser(description='Debug utility for VN',
                                     add_help=True)
    parser.set_defaults(**defaults)
    parser.add_argument('-cip', '--config_ip',
                        help='Config node ip address')
    parser.add_argument('-cport', '--config_port',
                        help='Config node REST API port')
    parser.add_argument('-obj', '--obj_type',
                        help='Object type to search')
    parser.add_argument('-uuid', '--uuid',
                        help='uuid')
    parser.add_argument('-dname', '--display_name',
                        help='Display name of the object')
    parser.add_argument('-fqn', '--fq_name',
                        help='Display name of the object')
    parser.add_argument('--detail',
                        help='Context detail output to console')
    cliargs = parser.parse_args(args)
    if len(args) == 0:
        parser.print_help()
        sys.exit(2)
    return cliargs

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vVN= debugVertexVN(config_ip=args.config_ip,
                       config_port=args.config_port,
                       uuid=args.uuid,
                       obj_type=args.obj_type,
                       display_name=args.display_name)
    context = vVN.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(context)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json(context)

