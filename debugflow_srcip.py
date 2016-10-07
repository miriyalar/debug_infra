#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
"""

import sys
from vertex_print import vertexPrint
from debugflow import debugVertexFlow
from debugip import debugVertexIP
from parser import ArgumentParser

class debugVertexFlowSrcIP(object):
    def __init__(self, context=None, source_ip=None,
                 source_vn=None, **kwargs):
        self.source_ip = source_ip
        self.source_vn = source_vn
        self.kwargs = kwargs
        self.flows = list()
        ip_vertex = debugVertexIP(instance_ip_address=self.source_ip,
                                  virtual_network=self.source_vn,
                                  **kwargs)
        self.context = ip_vertex.get_context()
        for hostname, inspect in ip_vertex.get_vrouters():
            self.flows.extend(inspect.get_matching_flows(src_ip=self.source_ip,
                                  src_vn=self.source_vn))
        self.flow_vertices = list()
        self.kwargs = kwargs

    def process(self):
        for flow in self.flows:
            flowvertex = debugVertexFlow(source_ip=flow['sip'],
                                         dest_ip=flow['dip'],
                                         source_vn=flow['src_vn_match'],
                                         dest_vn=flow['dst_vn_match'],
                                         **self.kwargs)
            flowvertex.process()
            self.flow_vertices.append(flowvertex)

    def print_vertex(self):
        vertices = list()
        for flowvertex in self.flow_vertices:
            vertices.append(flowvertex.fwdflow)
            vertices.append(flowvertex.revflow)
        vP = vertexPrint(vertices)
        vP.convert_json()

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Flow', add_help=True)
    parser.add_argument('--source_ip', help='Source IP of the flow', required=True)
    parser.add_argument('--source_vn', help='VN of the source IP')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFlow = debugVertexFlowSrcIP(**args)
    vFlow.process()
    vFlow.print_vertex()
