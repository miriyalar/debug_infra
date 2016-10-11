#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
This is service instance vertex to get information from control, config, schema, analytics 
and relevant compute nodes.
Input: 
   Mandatory: uuid | fqname | service chain fq name
Dependant vertexes:
"""

import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
import debugvm
import debugvmi

class debugVertexSI(baseVertex):
    vertex_type = 'service-instance'
    def __init__(self, **kwargs):
        self.sc_name = None
        self.dependant_vertexes = [debugvm.debugVertexVM, debugvmi.debugVertexVMI]
        super(debugVertexSI, self).__init__(**kwargs)

    def get_schema(self):
        schema_dict = {
                "service-chain": {
                        "sc_name": self.get_si_from_sc,
                },
        }
        return schema_dict

    def get_si_from_sc(self, sc_name):
        objs = list()
        self.sc_name = sc_name
        node = self.schema.get_nodes()[0]
        introspect = self.schema.get_inspect_h(node['ip_address'])
        service_chains = introspect.get_service_chains(sc_name)
        if not service_chains:
            raise Exception('Service chain not found')
        self.service_chain = service_chains[0]
        refs = {p['object_type']:p['object_fq_name']
                for p in self.service_chain['obj_refs']}
        for service_instance in refs['service_instance']:
             objs.append({'fq_name': service_instance})
        return objs

    def get_config_schema(self, vertex, schema_inspect_h):
        si = schema_inspect_h.get_service_instances(vertex['uuid'])[0]
        return {self.vertex_type: si}

    def process_self(self, vertex):
        props = self.get_attr('properties', vertex, subtype='schema')[0]
        prop = {p['property_name']:p.get('property') for p in props}
        vertex['st_mode'] = prop['service_mode']
        vertex['auto_policy'] = prop['auto_policy']
        left_vn = prop['left_network']
        right_vn = prop['right_network']
        node = self.schema.get_nodes()[0]
        schema = self.schema.get_inspect_h(node['ip_address'])
        si_name = vertex['fq_name']
        if vertex['st_mode'] == 'in-network-nat':
            vertex['natted_ips'] = list()
            schema_to_use = ['virtual_machine_back_refs.virtual_machine_interface_back_refs',
                             'port_tuples.virtual_machine_interface_back_refs']
            vmis, discard = self.config.get_object('service-instance',
                                          schema_to_use=schema_to_use,
                                          where='uuid=%s'%vertex['uuid'])
            for vmi in vmis:
                if not vmi:
                    continue
                vmi = vmi['virtual-machine-interface']
                if vmi['virtual_machine_interface_properties']['service_interface_type'] == 'right':
                    for iip_dict in vmi['instance_ip_back_refs']:
                        iip_id = iip_dict['uuid']
                        iip, discard = self.config.get_object('instance-ip', where='uuid='+iip_id)
                        iip = iip[0]['instance-ip']
                        if iip.get('instance_ip_secondary', False):
                            continue
                        vertex['natted_ips'].append(iip['instance_ip_address'])
            vertex['right_vrf'] = right_vn + ':' + right_vn.split(':')[-1]
            vertex['left_vrf'] = schema.get_vrfs_of_vn(left_vn, sc_uuid=self.sc_name,
                                                       si_name=vertex['fq_name'])[0]
        elif vertex['st_mode'] == 'in-network':
            vertex['right_vrf'] = schema.get_vrfs_of_vn(right_vn, sc_uuid=self.sc_name,
                                                        si_name=vertex['fq_name'])[0]
            vertex['left_vrf'] = schema.get_vrfs_of_vn(left_vn, sc_uuid=self.sc_name,
                                                       si_name=vertex['fq_name'])[0]
        vertex['vrouters'] = self.get_vrouters(vertex)

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for SI', add_help=True)
    parser.add_argument('--display_name', help='Display name')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vSI= debugVertexSI(**args)
    #context = vSI.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vSI)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_catalogue(context, False)
    #vP.convert_to_file_structure(context)
    vP.convert_json()
