#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
from argparse import RawTextHelpFormatter

class debugVertexSample(baseVertex):
    """
    This is sampple vertex.

    Input: 
         Mandatory: uuid | fq_name
         Optional: 
    Output:
         Console output and contrail_debug_output.json, logs are at debug_nodes.log
    Dependant vertexes:
         VM, VN, SG, IP...
    """

    # Whatever dependant vertexes to be processed after this vertex is processed
    # User has control of processing dependant object, depends on the depth specified during the invocation of
    # the vertex
    self.dependant_vertexes = ['debugVertexVM', 'debugVertexVN', 'debugVertexSG', 'debugVertexIP']

    # Type of vertex, typically, it will coincide with config type
    vertex_type = 'virtual-machine-interface'

    # non config obj, is to tell whether this object/uuid is present in config node or not
    # default is config obj (False), if you are working on non_config_obj make it to 'True'
    # non_config_obj 'True' also requires 'def locate_obj' method, 
    # check debugVertexflow.py or debugVertexsc.py for reference.
    non_config_obj = False

    # There are couple of abstract methods need to be defined for baseVertex inheritance
    # process_self and get_schema, the following are examples

    # processing self
    def process_self(self, vertex):
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex)
        self._add_agent_to_context(vertex, agent)
        control = {}
        control['oper'] = {}
        self._add_control_to_context(vertex, control)

    # If user passes different object type's elements, we need to get the samplevertexes from it.
    # Example is for VMI vertex, if user passes different type of objects, how to get the VMI from it.
    # User doesn't have to define, it is the same type
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
        }
        return schema_dict


    # get_agent_oper_db is repeated for all the agents relavant for this type
    def _get_agent_oper_db(self, introspect, vertex):
        error = False
        oper = {}
        vmi_uuid = vertex['uuid']
        intf_details = introspect.get_intf_details(vmi_id=vmi_uuid)
        if len(intf_details['ItfResp']['itf_list']) == 1:
            intf_rec = intf_details['ItfResp']['itf_list'][0]
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

        oper['interface'] = intf_details
        return oper

def parse_args(args):
    parser = ArgumentParser(description=debugVertexSample.__doc__, add_help=True, formatter_class=RawTextHelpFormatter)
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vSample= debugVertexSample(**args)
    # Vertex Print object for json/file structure display of processed objects
    vP = vertexPrint(vSample)
    vP.convert_json()
    vP.convert_to_file_structure()
