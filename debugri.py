#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
This is RI vertex to get RI information from config, control and relevant compute nodes
Input: 
   Mandatory: uuid | fq_name
Dependant vertexes:
   VN
"""

import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
import debugvn

class debugVertexRI(baseVertex):
    vertex_type = 'routing-instance'
    def __init__(self, **kwargs):
        self.dependant_vertexes = [debugvn.debugVertexVN]
        super(debugVertexRI, self).__init__(**kwargs)

    def process_self(self, vertex):
        pass

    def get_schema(self, **kwargs):
        #VN UUID, VMI UUID
        schema_dict = {
            "virtual-network": {
                "uuid": 'routing_instances'
            },
            "virtual-machine-interface": {
                "uuid": 'routing_instance_refs'
            }
        }
        return schema_dict

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Routing Instance', add_help=True)
    parser.add_argument('--display_name', help='Display name')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vRI= debugVertexRI(**args)
    #context = vVN.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vRI)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json()
