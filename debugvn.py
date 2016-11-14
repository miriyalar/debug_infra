#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
from argparse import RawTextHelpFormatter
import debugvmi
import debugri

class debugVertexVN(baseVertex):
    """
    This is VN vertex to get VN information from config, control and relevant compute nodes
    Input: 
         Mandatory: uuid | (object-type, uuid) [object_type and uuid has to be there in the schema_dict]
    Output:
         Console output, debug_nodes.log and contrail_debug_output.json
    Dependant vertexs:
         VMI, RI
    """
    vertex_type = 'virtual-network'

    def __init__(self, **kwargs):
        dependant_vertexes = [debugvmi.debugVertexVMI, debugri.debugVertexRI]
        super(debugVertexVN, self).__init__(**kwargs)

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

    def process_self(self, vertex):
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex)
        self._add_agent_to_context(vertex, agent)
        control = {}
        control['oper'] = {}
        self._add_control_to_context(vertex, control)

    def _get_agent_oper_db(self, introspect, vertex):
        error = False
        vn_uuid = vertex['uuid']
        oper = {}
        vn_info = introspect.get_vn_details(vn_uuid)
        if len(vn_info['vn_list'] or []) == 1:
            vn_rec = vn_info['vn_list'][0]
            oper[vertex['vertex_type']] = vn_rec
        else:
            error = True
            pstr = "Got more vn records, supposed to have one for uuid %s" % (vn_uuid)
            self.logger.error(pstr)
        pstr = "Agent Verified virtual network %s %s" % (vn_uuid, 'with errors' if error else '')
        self.logger.info(pstr)
        return oper

def parse_args(args):
    parser = ArgumentParser(description=debugVertexVN.__doc__, add_help=True, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--display_name', help='Display name')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vVN= debugVertexVN(**args)
    vP = vertexPrint(vVN)
    vP.convert_json()
