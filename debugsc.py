#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
from argparse import RawTextHelpFormatter
import debugsi

class debugVertexSC(baseVertex):
    """
    Debug utility for SC.

    This is non config service chain vertex to debug service chain/s.
    Input:
         Mandatory: left_vn, right_vn
    Output:
         Console output and contrail_debug_output.json, logs are at debug_nodes.log
    Dependant vertexes:
         None 
    """

    vertex_type = 'service-chain'
    non_config_obj = True
    def __init__(self, left_vn_fq_name=None, right_vn_fq_name=None,
                 context=None, **kwargs):
        self.dependant_vertexes = [debugsi.debugVertexSI]
        self.left_vn = left_vn_fq_name
        self.right_vn = right_vn_fq_name
        self.match_kv = {'dummy': 'dummy'}
        self.service_chain = dict()
        self.si_vertex = dict()
        super(debugVertexSC, self).__init__(context=context, **kwargs)

    def get_schema(self):
        pass

    def get_vrouter_info(self, vertex):
        pass

    def get_uuid(self, sc_name):
        return sc_name

    def locate_obj(self):
        node = self.schema.get_nodes()[0]
        inspect = self.schema.get_inspect_h(node['ip_address'])
        if self.element is not None:
            self.left_vn = self.element['left_vn']
            self.right_vn = self.element['right_vn']
        if not self.left_vn or not self.right_vn or \
           (self.left_vn == self.right_vn):
            return []
        service_chains = inspect.get_service_chains(vn_list=[self.left_vn, self.right_vn])
        if not service_chains:
            self.logger.info('no service chains found between %s and %s' % (self.left_vn,
                                                                            self.right_vn))
        objs = list()
        for service_chain in service_chains or []:
            sc_name = service_chain['object_fq_name']
            uuid = self.get_uuid(sc_name)
            self.service_chain[uuid] = service_chain
            objs.append({self.vertex_type: {'sc_name': sc_name,
                                            'uuid': uuid}})
        return objs

    def store_config(self, vertex):
        vdict = vertex['config']['schema'] = dict()
        vdict.update({self.schema.node['hostname']: self.service_chain[vertex['uuid']]})

    def process_self(self, vertex):
        uuid = vertex['uuid']
        refs = {p['object_type']:p['object_fq_name']
                for p in self.service_chain[uuid]['obj_refs']}
        sis = self.si_vertex[uuid] = [self.context.get_vertex_of_fqname(fqname, 'service-instance')
                                      for fqname in refs['service_instance']]
        vertex['path'] = []
        for si in sis:
            si_path = dict()
            si_path['vrouters'] = si['vrouters']
            si_path['natted_ips'] = si['natted_ips']
            si_path['left_vrf'] = si['left_vrf']
            si_path['right_vrf'] = si['right_vrf']
            si_path['si_name'] = si['fq_name']
            vertex['path'].append(si_path)

def parse_args(args):
    parser = ArgumentParser(description=debugVertexSC.__doc__, add_help=True, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--left_vn_fq_name', help='FQName of the Left VN', required=True)
    parser.add_argument('--right_vn_fq_name', help='FQName of the Right VN', required=True)
    parser.add_argument('--left_ip', help='Left CIDR specified in policy')
    parser.add_argument('--right_ip', help='Right CIDR specified in policy')
    parser.add_argument('--protocol', help='L3 Protocol of the flow')
    parser.add_argument('--left_port', help='Source Port of the flow')
    parser.add_argument('--right_port', help='Destination Port of the flow')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vSC= debugVertexSC(**args)
    vP = vertexPrint(vSC)
    vP.convert_json()
