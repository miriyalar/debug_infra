#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
This is VMI debug vertex to debug VMI in the contrail.
Gets information from config, control, analytics and relevant compute nodes
Input: 
   Mandatory: uuid | (object-type, uuid) [object_type and uuid has to be there in the schema_dict]
Dependant vertexes:
   VM, VN, SG, IP
"""

import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
import debugvm
import debugvn
import debugsg
import debugip

class debugVertexVMI(baseVertex):
    vertex_type = 'virtual-machine-interface'

    def __init__(self, **kwargs):
        self.dependant_vertexes = [debugvm.debugVertexVM, debugvn.debugVertexVN, debugsg.debugVertexSG, debugip.debugVertexIP]
        super(debugVertexVMI, self).__init__(**kwargs)

    def get_schema(self):
        #VM UUID, VMI UUID, VMI Name, VN UUID
        schema_dict = {
                'virtual-machine': {
                    'uuid': 'virtual_machine_interface_back_refs'
                },
                'virtual-network': {
                    'uuid': 'virtual_machine_interface_back_refs',
                    'display_name': 'virtual_machine_interface_back_refs'
                },
                'security-group': {
                    'uuid': 'virtual_machine_interface_back_refs'
                },
                'floating-ip': {
                    'uuid': 'virtual_machine_interface_refs'
                },
                'instance-ip': {
                    'uuid': 'virtual_machine_interface_refs'
                },
                'service-instance': {
                    'uuid': 'port_tuples.virtual_machine_interface_back_refs'
                },
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
        oper = {}
        vmi_uuid = vertex['uuid']
        intf_details = introspect.get_intf_details(vmi_id=vmi_uuid)
        if not intf_details:
            return oper
        if len(intf_details.get('itf_list') or []) == 1:
            intf_rec = intf_details['itf_list'][0]
        else:
            pstr = "Agent Error interface uuid %s, doesn't exist" % (vmi_uuid)
            error = True
            self.logger.error(pstr)
            print pstr
            return oper

        # Is interface active
        if intf_rec['active'] != 'Active':
            pstr = "Agent Error %s, %s is not Active" % (intf_rec['uuid'], intf_rec['name'])
            error = True
            self.logger.error(pstr)
            print pstr
        else:
            pstr = "Agent: Interface %s is active" % (intf_rec['name'])
            self.logger.debug(pstr)
            print pstr

        # Is dhcp enabled
        if intf_rec['dhcp_service'] != 'Enable':
            pstr = "Agent Error %s, %s, dhcp is %s, but not enabled" % \
                   (intf_rec['uuid'], intf_rec['name'], intf_rec['dhcp_service'])
            error = True
            self.logger.error(pstr)
            print pstr
        else:
            self.logger.debug("Agent: Interface %s dhcp is enabled" % (intf_rec['name']))

        # Is dns enabled
        if intf_rec['dns_service'] != 'Enable':
            pstr = "Agent Error %s, %s, dns is %s, but not enabled" % \
                (intf_rec['uuid'], intf_rec['name'], intf_rec['dns_service'])
            error = True
            self.logger.error(pstr)
            print pstr
        else:
            self.logger.debug("Agent: Interface %s dns is enabled" % (intf_rec['name']))

        pstr = "Agent Verified interface %s %s" % (intf_rec['name'], 'with errors' if error else '')
        self.logger.debug(pstr)
        print pstr
        oper['interface'] = intf_details
        return oper

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for VMI', add_help=True)
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vVMI= debugVertexVMI(**args)
    #context = vVMI.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vVMI)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, True)
    vP.convert_json()
    vP.convert_to_file_structure(console_print=True)
