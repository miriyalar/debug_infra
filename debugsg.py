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

class debugVertexSG(baseVertex):
    """
    Debug utility for SG.

    This is security group vertex and gets SG information from config, control and relevant compute nodes.
    Input:
         Mandatory: uuid | (object_type, uuid) [object_type and uuid has to be there in the schema_dict]
    Output:
         Console output and contrail_debug_output.json, logs are at debug_nodes.log
    Dependant vertexes:
         VMI
    """

    vertex_type = 'security-group'
    def __init__(self, **kwargs):
        self.dependant_vertexes = [debugvmi.debugVertexVMI]
        super(debugVertexSG, self).__init__(**kwargs)

    def get_schema(self):
        schema_dict = {
                "virtual-machine": {
                        "uuid": 'virtual_machine_interface_back_refs.security_group_refs'
                },
                "virtual-machine-interface": {
                        "uuid": 'security_group_refs'
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
        sg_uuid = vertex['uuid']
        oper = {}
        sg_info = introspect.get_sg_details(sg_uuid)
        if len(sg_info['sg_list'] or []) == 1:
            sg_rec = sg_info['sg_list'][0]
            oper[vertex['vertex_type']] = sg_rec
        else:
            return oper

        egress_acl_uuid = sg_rec['egress_acl_uuid']
        ingress_acl_uuid = sg_rec['ingress_acl_uuid']
        url_dict_resp = introspect.get_acl_details(egress_acl_uuid)
        if len(url_dict_resp['acl_list']) == 1:
            egress_acl_rec = url_dict_resp['acl_list'][0]
            oper['egress_acl'] = egress_acl_rec
        else:
            error = True

        url_dict_resp = introspect.get_acl_details(ingress_acl_uuid)
        if len(url_dict_resp['acl_list']) == 1:
            ingress_acl_rec = url_dict_resp['acl_list'][0]
            oper['ingress_acl'] = ingress_acl_rec
        else:
            error = True
        pstr = "Agent Verified security group %s %s" % (sg_uuid, 'with errors' if error else '')
        self.logger.info(pstr)
        return oper


def parse_args(args):
    parser = ArgumentParser(description=debugVertexSG.__doc__, add_help=True, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--display_name', help='Display name')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vSG= debugVertexSG(**args)
    vP = vertexPrint(vSG)
    vP.convert_json()
