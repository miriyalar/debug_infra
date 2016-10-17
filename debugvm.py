#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
This is VM debug vertex to debug VM in the contrail.
Gets information from config, control and relevant compute nodes
Input: 
   Mandatory: uuid | (object-type, uuid) [object_type and uuid has to be there in the schema_dict]
Dependant vertexes:
   VMI
"""

import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
import debugvmi

class debugVertexVM(baseVertex):
    vertex_type = 'virtual-machine'
    def __init__(self, **kwargs):
        self.dependant_vertexes = [debugvmi.debugVertexVMI]
        super(debugVertexVM, self).__init__(**kwargs)

    def get_schema(self):
        #VMI, VM name, VM UUID
        schema_dict = {
                "virtual-machine-interface": {
                    'uuid': 'virtual_machine_refs',
                    'display_name': 'virtual_machine_refs',
                },
                "service-instance": {
                    'uuid': 'virtual_machine_back_refs'
                }
        }
        return schema_dict

    def process_self(self, vertex):
        # Agent
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex)
        self._add_agent_to_context(vertex, agent)
        control = {}
        self._add_control_to_context(vertex, control)

    def _get_agent_oper_db(self, introspect, vertex):
        oper = {}
        vm_uuid = vertex['uuid']
        vm_info = introspect.get_vm_details(vm_uuid)
        oper['vm'] = vm_info
        if len(vm_info['vm_list'] or []) == 1:
            vm_rec = vm_info['vm_list'][0]
            if vm_uuid == vm_rec['uuid']:
                pstr  = "Agent VM %s is present" % (vm_uuid)
                self.logger.debug(pstr)
                print pstr
        else:
            pstr = "Agent VM uuid %s NOT FOUND" % (vm_uuid)
            self.logger.error(pstr)
            print pstr
        return oper

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for VM', add_help=True)
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vVM= debugVertexVM(**args)
    #context = vVM.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vVM)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_catalogue(context, True)
    vP.convert_json()
    #vP.convert_to_file_structure(context)
