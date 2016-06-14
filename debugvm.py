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

class debugVertexVM(baseVertex):
    dependant_vertexes = ['debugVertexVMI']
    def __init__(self, context=None, **kwargs):
        self.vertex_type = 'virtual-machine'
        self.obj_type = 'virtual-machine'
        super(debugVertexVM, self).__init__(context, self.vertex_type, **kwargs)
        if self._is_vertex_type_exists_in_path(self.vertex_type):
            return
        self.logger = logger(logger_name=self.get_class_name()).get_logger()
        obj_type = kwargs.get('obj_type', None)
        if not obj_type:
            obj_type = self.obj_type
        self.display_name = kwargs.get('display_name', None)
        self.uuid = kwargs.get('uuid', None)
        vms = self._locate_vm(context=self.context, 
                              element = self.element, 
                              obj_type=obj_type, 
                              uuid=self.uuid,
                              display_name=self.display_name)
        self.process_vertexes(self.vertex_type, vms, self.dependant_vertexes)


    def _locate_vm(self, context, element=None, **kwargs):
        #VMI, VM name, VM UUID
        schema_dict = {
                "virtual-machine-interface": {
                    'uuid': 'virtual_machine_refs',
                    'display_name': 'virtual_machine_refs',
                }
        }
        #Input_dict
        obj_list = self._locate_obj(schema_dict, element, **kwargs)
        return obj_list

    def _process_self(self, vertex_type, uuid, vertex):
        # Agent
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex_type, vertex)
        self._add_agent_to_context(uuid, agent)
        control = {}
        self._add_control_to_context(uuid, control)

    def _get_agent_oper_db(self, host_ip, agent_port, vertex_type, vertex):
        base_url = 'http://%s:%s/%s' % (host_ip, agent_port, 'Snh_VmListReq?')
        vm_uuid = vertex[vertex_type]['uuid']
        search_str = ('uuid=%s') % (vm_uuid)
        oper = {}
        url_dict_resp = Introspect(url=base_url + search_str).get()
        oper['vm'] = url_dict_resp
        if len(url_dict_resp['VmListResp']['vm_list']) == 1:
            vm_rec = url_dict_resp['VmListResp']['vm_list'][0]
            if vm_uuid == vm_rec['uuid']:
                pstr  = "Agent VM %s is present" % (vm_uuid)
                self.logger.debug(pstr)
                print pstr
        else:
            pstr = "Agent VM uuid % NOT FOUND" % (vm_uuid)
            self.logger.error(pstr)
            print pstr
        return oper


def parse_args(args):
    defaults = {
        'config_ip': '127.0.0.1',
        'config_port': '8082',
        'detail': False,        
    }
    parser = argparse.ArgumentParser(description='Debug utility for VM',
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
    parser.add_argument('--detail',
                        help='Context detail output to console')
    cliargs = parser.parse_args(args)
    if len(args) == 0:
        parser.print_help()
        sys.exit(2)
    return cliargs

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vVM= debugVertexVM(config_ip=args.config_ip,
                       config_port=args.config_port,
                       uuid=args.uuid,
                       obj_type=args.obj_type,
                       display_name=args.display_name)
    context = vVM.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(context)
    #vP._visited_vertexes_brief(context)
    vP.print_visited_nodes(context, detail=False)
    #vP.print_object_catalogue(context, True)
    vP.convert_json(context)

