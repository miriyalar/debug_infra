'''
Take context as argument, in addition to regular input of 4-tuple
Create a uuid, fq_name for a flow and stick in the vertex
base flow verter class?
should we create a singleton object for context and use it at baseVertex and baseFlowVertex

'''

import sys
import argparse
from logger import logger
from basevertex import baseVertex
from parser import ArgumentParser
from debugip import debugVertexIP
from vertex_print import vertexPrint
from utils import DictDiffer
import time

class debugVertexFlow(object):
    vertex_type = 'flow'
    def __init__(self, **kwargs):
        self.logger = logger(logger_name=self.__class__.__name__).get_logger()
        self.source_ip = kwargs.pop('source_ip', None)
        self.dest_ip = kwargs.pop('dest_ip', None)
        self.source_vn = kwargs.pop('source_vn', None)
        self.dest_vn = kwargs.pop('dest_vn', None)
        self.protocol = kwargs.pop('protocol', None)
        self.source_port = kwargs.pop('source_port', None)
        self.dest_port = kwargs.pop('dest_port', None)
        self.srcip_vertex = debugVertexIP(instance_ip_address=self.source_ip, **kwargs)
        self.context = self.srcip_vertex.get_context()
        self.destip_vertex = debugVertexIP(instance_ip_address=self.dest_ip,
                                           context=self.context, **kwargs)
        self.src_vn_fqname = self.srcip_vertex.get_attr('virtual_network_refs.0.to')
        self.dest_vn_fqname = self.destip_vertex.get_attr('virtual_network_refs.0.to')
        self.source_vrf = ':'.join(self.src_vn_fqname+self.src_vn_fqname[-1:])
        self.dest_vrf = ':'.join(self.dest_vn_fqname+self.dest_vn_fqname[-1:])
        self.check_routes()
        self.check_flowtable()
        self.check_dropstats()
        self.vertexes = []
        self.vertexes.extend(self.srcip_vertex.get_vertex())
        self.vertexes.extend(self.destip_vertex.get_vertex())

#        src_agent_oper = self._get_agent_oper_db(src_vrouter['hostname'] + ':src',
#                                                 src_vrouter['ip_address'], src_vrouter['sandesh_http_port'],
#                                                 srcip_uuid, self.source_ip)
#        dest_agent_oper = self._get_agent_oper_db(dest_vrouter['hostname'] + ':dest',
#                                                  dest_vrouter['ip_address'], dest_vrouter['sandesh_http_port'],
#                                                  destip_uuid, self.dest_ip)

    def check_routes(self):
        for inspect in self.srcip_vertex.get_vrouters():
            assert inspect.is_route_exists(self.source_vrf, self.dest_ip), 'route doesnt exist'
            print 'route exists'

        for inspect in self.destip_vertex.get_vrouters():
            assert inspect.is_route_exists(self.dest_vrf, self.source_ip), 'route doesnt exist'
            print 'route exists'

    def check_flowtable(self):
        sflows = list(); dflows=list()
        for inspect in self.srcip_vertex.get_vrouters():
            flow = inspect.get_matching_flows(self.source_ip, self.dest_ip,
                                              self.protocol, self.source_port,
                                              self.dest_port, ':'.join(self.src_vn_fqname),
                                              ':'.join(self.dest_vn_fqname))
            if flow:
                sflows.extend(flow)
                self.src_vrouter_h = inspect
        for inspect in self.destip_vertex.get_vrouters():
            flow = inspect.get_matching_flows(self.source_ip, self.dest_ip,
                                              self.protocol, self.source_port,
                                              self.dest_port, ':'.join(self.src_vn_fqname),
                                              ':'.join(self.dest_vn_fqname))
            if flow:
                dflows.extend(flow)
                self.dst_vrouter_h = inspect

        for flow in sflows:
            print 'sg_action', flow['sg_action_summary'][0]['action']
            print 'action_str', flow['action_str'][0]['action']
            print 'action', flow['action']
        for flow in dflows:
            print 'sg_action', flow['sg_action_summary'][0]['action']
            print 'action_str', flow['action_str'][0]['action']
            print 'action', flow['action']

    def check_dropstats(self):
        initial = self.src_vrouter_h.get_dropstats()
        diffset = list()
        for i in range(2):
            time.sleep(5)
            current = self.src_vrouter_h.get_dropstats()
            diffset.append({key:current[key]
                           for key in DictDiffer(current, initial).changed()})
        print initial
        for diff in diffset:
            print diff

    def get_context(self):
        return self.context

    def get_vertex(self):
        return self.vertexes

    def get_dependent_vertices(self):
        return []

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Flow', add_help=True)
    parser.add_argument('--source_ip', help='Source IP of the flow', required=True)
    parser.add_argument('--dest_ip', help='Destination IP of the flow', required=True)
    parser.add_argument('--source_vn', help='VN of the source IP')
    parser.add_argument('--dest_vn', help='VN of the destination IP')
    parser.add_argument('--protocol', help='L3 Protocol of the flow')
    parser.add_argument('--source_port', help='Source Port of the flow')
    parser.add_argument('--dest_port', help='Destination Port of the flow')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFlow= debugVertexFlow(**args)

    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vFlow)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json()

