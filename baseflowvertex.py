'''
Take context as argument, in addition to regular input of 4-tuple
Create a uuid, fq_name for a flow and stick in the vertex
base flow verter class?
should we create a singleton object for context and use it at baseVertex and baseFlowVertex

'''

import sys
import argparse
from collections import defaultdict
from logger import logger
from parser import ArgumentParser
from debugip import debugVertexIP
from vertex_print import vertexPrint
from utils import DictDiffer
from basevertex import create_global_context, get_logger, create_vertex
import time

class baseFlowVertex(object):
    vertex_type = 'flow'
    def __init__(self, context=None, **kwargs):
        self.logger = get_logger(name=self.__class__.__name__, **kwargs)
        self.source_ip = kwargs.pop('source_ip', None)
        self.dest_ip = kwargs.pop('dest_ip', None)
        self.source_vn = kwargs.pop('source_vn', None)
        self.dest_vn = kwargs.pop('dest_vn', None)
        self.source_vrf = kwargs.pop('source_vrf', None)
        self.dest_vrf = kwargs.pop('dest_vrf', None)
        self.protocol = kwargs.pop('protocol', None)
        self.source_port = kwargs.pop('source_port', None)
        self.dest_port = kwargs.pop('dest_port', None)
        if not context:
            self.context = create_global_context(**kwargs)
        else:
            self.context = context
        self.vertex = create_vertex(self.vertex_type,
                                    srcip_dstip='_'.join([self.source_ip, self.dest_ip]))
        self.srcip_vertex = debugVertexIP(instance_ip_address=self.source_ip,
                                          context=self.context, **kwargs)
        self.destip_vertex = debugVertexIP(instance_ip_address=self.dest_ip,
                                           context=self.context, **kwargs)
        if not self.source_vrf:
            self.src_vn_fqname = self.srcip_vertex.get_attr('virtual_network_refs.0.to')
            if not self.src_vn_fqname:
                raise Exception('Unable to fetch VN info from IP address')
            self.source_vrf = ':'.join(self.src_vn_fqname+self.src_vn_fqname[-1:])
        else:
            self.src_vn_fqname = self.source_vrf.split(':')[:-1]

        if not self.dest_vrf:
            self.dest_vn_fqname = self.destip_vertex.get_attr('virtual_network_refs.0.to')
            if not self.src_vn_fqname:
                raise Exception('Unable to fetch VN info from IP address')
            self.dest_vrf = ':'.join(self.dest_vn_fqname+self.dest_vn_fqname[-1:])
        else:
            self.dest_vn_fqname = self.dest_vrf.split(':')[:-1]
        self.process_vertex()

    def process_vertex(self):
        self.check_routes()
        self.check_flowtable()
        self.check_dropstats()

    def check_routes(self):
        oper = defaultdict(dict)
        for inspect in self.srcip_vertex.get_vrouters():
            (check, route) = inspect.is_route_exists(self.source_vrf, self.dest_ip)
            if not check:
                print 'route for destip %s doesnt exist in source vrf %s'%(self.dest_ip, self.source_vrf)
            print 'route exists for destip %s in source vrf %s'%(self.dest_ip, self.source_vrf)
            oper['src_route'][inspect._ip] = route

        for inspect in self.destip_vertex.get_vrouters():
            (check, route) = inspect.is_route_exists(self.dest_vrf, self.source_ip)
            if not check:
                print 'route for srcip %s doesnt exist in dest vrf %s'%(self.source_ip, self.dest_vrf)
            print 'route exists for srcip %s in dest vrf %s'%(self.source_ip, self.dest_vrf)
            oper['dst_route'][inspect._ip] = route
        self.vertex['agent']['oper'].update(oper)

    def check_flowtable(self):
        sflows = list(); dflows=list()
        oper = defaultdict(dict)
        for inspect in self.srcip_vertex.get_vrouters():
            flow = inspect.get_matching_flows(self.source_ip, self.dest_ip,
                                              self.protocol, self.source_port,
                                              self.dest_port, ':'.join(self.src_vn_fqname),
                                              ':'.join(self.dest_vn_fqname))
            if flow:
                print 'Found matching flow on source agent'
                sflows.extend(flow)
            else:
                print 'Unable to find matching flow on src agent %s'%inspect._ip
            oper['src_flow'][inspect._ip] = flow

        for inspect in self.destip_vertex.get_vrouters():
            flow = inspect.get_matching_flows(self.source_ip, self.dest_ip,
                                              self.protocol, self.source_port,
                                              self.dest_port, ':'.join(self.src_vn_fqname),
                                              ':'.join(self.dest_vn_fqname))
            if flow:
                print 'Found matching flow on destination agent'
                dflows.extend(flow)
            else:
                print 'Unable to find matching flow on dest agent %s'%inspect._ip
            oper['dst_flow'][inspect._ip] = flow

        self.vertex['agent']['oper'].update(oper)
        for flow in sflows:
            if flow['sg_action_summary'][0]['action'] != 'pass':
                print 'SG drop'
            if flow['action_str'][0]['action'] != 'pass':
                print 'Flow action Drop'
        for flow in dflows:
            if flow['sg_action_summary'][0]['action'] != 'pass':
                print 'SG drop'
            if flow['action_str'][0]['action'] != 'pass':
                print 'Flow action Drop'

    def check_dropstats(self):
        oper = defaultdict(dict)
        dropstats = defaultdict(dict)
        for vrouter in self.srcip_vertex.get_vrouters():
            dropstats['src_initial'][vrouter._ip] = vrouter.get_dropstats()
        for vrouter in self.destip_vertex.get_vrouters():
            dropstats['dst_initial'][vrouter._ip] = vrouter.get_dropstats()
        for i in range(2):
            #time.sleep(5)
            for vrouter in self.srcip_vertex.get_vrouters():
                current = vrouter.get_dropstats()
                initial = dropstats['src_initial'][vrouter._ip]
                dropstats['src_diff_'+str(i)] = {key:current[key]
                          for key in DictDiffer(current, initial).changed()}
            for vrouter in self.destip_vertex.get_vrouters():
                current = vrouter.get_dropstats()
                initial = dropstats['dst_initial'][vrouter._ip]
                dropstats['dst_diff_'+str(i)] = {key:current[key]
                          for key in DictDiffer(current, initial).changed()}
        oper['dropstats'] = dropstats
        self.vertex['agent']['oper'].update(oper)

    def get_context(self):
        return self.context

    def get_vertex(self):
        return [self.vertex]

    def get_dependent_vertices(self):
        vertices = [self.srcip_vertex, self.destip_vertex]
        return vertices

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
    vFlow= baseFlowVertex(**args)
#    vFlow.process_vertex()

    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vFlow)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json()

