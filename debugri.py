#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
import debugvn
from argparse import RawTextHelpFormatter

class debugVertexRI(baseVertex):
    """
    Debug utility for Routing Instance.

    This is RI vertex to get RI information from config, control and relevant compute nodes.
    Input: 
         Mandatory: uuid | fq_name
    Output:
         Console output and contrail_debug_output.json, logs are at debug_nodes.log
    Dependant vertexes:
         VN
    """

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
    parser = ArgumentParser(description=debugVertexRI.__doc__, add_help=True, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--display_name', help='Display name')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vRI= debugVertexRI(**args)
    vP = vertexPrint(vRI)
    vP.convert_json()
