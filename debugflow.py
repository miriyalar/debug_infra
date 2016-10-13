#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
This is non config debugflow vertex to debug a given flow with 2 tuple to 7 tuple
If the flow has service chain attached, it is required to give left and right VN of the flow.
Input:
   Mandatory: 3 tuple (source VN, source IP, dest IP)
   Optional: Rest of 7 tuples (dest VN, source port, dest port, protocol)
             ip_type is optional, takes 'instance-ip' or 'floating-ip',
             default is 'instance-ip'
Dependant vertexes:
"""

import sys
from vertex_print import vertexPrint
from baseflowvertex import baseFlowVertex
from parser import ArgumentParser
from basevertex import baseVertex
from debugip import debugVertexIP
from debugfip import debugVertexFIP
import debugsc

class debugVertexFlow(baseVertex):
    vertex_type = 'flow'
    non_config_obj = True
    ip_type = ['instance-ip', 'floating-ip', 'external']
    def __init__(self, context=None, source_ip='', dest_ip='',
                 source_vn='', dest_vn='', protocol='',
                 source_port='', dest_port='', **kwargs):
        self.dependant_vertexes = [debugsc.debugVertexSC]
        self.source_ip = source_ip
        self.dest_ip = dest_ip
        self.source_vn = source_vn
        self.dest_vn = dest_vn
        self.protocol = protocol
        self.source_port = source_port
        self.dest_port = dest_port
        self.source_nip = kwargs.get('source_nip', '')
        self.dest_nip = kwargs.get('dest_nip', '')
#        self.source_vrf = kwargs.get('source_vrf', '')
#        self.dest_vrf = kwargs.get('dest_vrf', '')
#        self.source_nvrf = kwargs.get('source_nvrf', '')
#        self.dest_nvrf = kwargs.get('dest_nvrf', '')
        self.source_ip_type = kwargs.get('source_ip_type', '')
        self.dest_ip_type = kwargs.get('dest_ip_type', '')
        self.match_kv = {'source_ip': source_ip, 'dest_ip': dest_ip}
        if not self.source_vn and not self.dest_vn:
            raise Exception('Please specify VN FQNames')
        if not self.source_vn:
            self.source_vn = self.dest_vn
        if not self.dest_vn:
            self.dest_vn = self.source_vn
        self.source_vrf = self.source_vn + ':' + self.source_vn.split(':')[-1]
        self.dest_vrf = self.dest_vn + ':' + self.dest_vn.split(':')[-1]
        super(debugVertexFlow, self).__init__(context=context, **kwargs)

    def get_schema(self):
        pass

    def get_uuid(self):
        return ':'.join(['flow', self.source_ip, self.source_nip,
                         self.dest_ip, self.dest_nip,
                         self.source_vrf, self.dest_vrf,
                         self.source_port, self.dest_port,
                         self.protocol])
# self.source_nvrf, self.dest_nvrf,

    def _get_vertex(self, address=None, ip_type=None, vn_fqname=None):
        vertex = None
        if not vn_fqname or not address:
            return None
        if ip_type not in self.ip_type:
            ip_type = self.config.get_ip_type(address, vn_fqname)

        if ip_type == 'instance-ip':
            vertex = debugVertexIP(instance_ip_address=address,
                                   virtual_network=vn_fqname,
                                   context=self.context)
        elif ip_type == 'floating-ip':
            vertex = debugVertexFIP(floating_ip_address=address,
                                    virtual_network=vn_fqname,
                                    context=self.context)
        elif ip_type == 'external':
            pass
        else:
            self.logger.error('ip type %s is not expected, ip = %s, vn = %s' % (
                              ip_type, address, vn_fqname))
        return vertex

    def locate_obj(self):
        srcip_vertex = self._get_vertex(self.source_ip,
                                        self.source_ip_type,
                                        self.source_vn)
        destip_vertex = self._get_vertex(self.dest_ip,
                                         self.dest_ip_type,
                                         self.dest_vn)
        # Get vRouter info from the vertex
        if srcip_vertex and srcip_vertex.vertexes:
            vertex = srcip_vertex.vertexes[0]
            left_vn = ':'.join(self.get_attr('virtual_network_refs.0.to', vertex)[0])
            self.srcip_vrouters = srcip_vertex.get_vrouters(vertex)
        else:
            self.srcip_vrouters = None
            left_vn = self.source_vn

        if destip_vertex and destip_vertex.vertexes:
            vertex = destip_vertex.vertexes[0]
            right_vn = ':'.join(self.get_attr('virtual_network_refs.0.to', vertex)[0])
            self.destip_vrouters = destip_vertex.get_vrouters(vertex)
        else:
            self.destip_vrouters = None
            right_vn = self.dest_vn

        objs = list()
        objs.append({self.vertex_type: {'uuid': self.get_uuid(),
                                        'left_vn': left_vn,
                                        'right_vn': right_vn
                                        }})
        return objs

    def store_config(self, vertex):
        pass

    def get_vrouter_info(self, vertex):
        pass

    def get_path(self):
        path = list()
        sc_vertexes = list()
        pleft_vrf = self.source_vrf
        pright_vrf = self.dest_vrf
        for dep_vertex_objs in self.get_dependent_vertices():
             if dep_vertex_objs.vertexes:
                 sc_vertexes.extend(dep_vertex_objs.vertexes)
        if self.srcip_vrouters:
            source = {'sip': self.source_ip,
                      'dip': self.dest_ip,
                      'source_vrf': self.source_vrf,
                      'vrouters': self.srcip_vrouters,
                      'dest_vrf': self.dest_vrf
                     }
            path.append(source)
        natted_ips = None
        if sc_vertexes:
            initial = True
            # Do the service chain path
            for sc_vertex in sc_vertexes:
                for si_path in sc_vertex['path']:
                    if initial:
                        if path:
                            path[-1]['dest_vrf'] = si_path['left_vrf']
                        initial = False
                    pleft = {'vrouters': si_path['vrouters'],
                             'source_vrf': pleft_vrf,
                             'dest_vrf': si_path['left_vrf'],
                             'sip': self.source_ip,
                             'dip': self.dest_ip,
                             'dnip': natted_ips,
                             'si-name': si_path['si_name']
                             }
                    natted_ips = si_path.get('natted_ips', [])
                    pright = {'vrouters': si_path['vrouters'],
                              'source_vrf': pright_vrf,
                              'dest_vrf': si_path['right_vrf'],
                              'sip': self.source_ip,
                              'dip': self.dest_ip,
                              'snip': natted_ips,
                              'si-name': si_path['si_name']
                             }
                    path.append(pleft)
                    path.append(pright) 
        if self.destip_vrouters:
            dest = {'sip': self.source_ip,
                    'dip': self.dest_ip,
                    'source_vrf': self.dest_vrf,
                    'dest_vrf': path[-1]['dest_vrf'] if path else self.dest_vrf,
                    'snip': natted_ips,
                    'vrouters': self.destip_vrouters
                   }
            path.append(dest)
        return path
 
    def process_self(self, vertex):
        vertex['path'] = self.get_path()
        # Trace the expected packet flow path
        for path in vertex['path']:
            baseFlowVertex(context=self.context,
                           vrouters=path['vrouters'],
                           source_ip=path['sip'],
                           dest_ip=path['dip'], 
                           source_vrf=path['source_vrf'],
                           dest_vrf=path['dest_vrf'],
                           source_nip=path.get('snip'),
                           dest_nip=path.get('dnip'),
                           source_vn=self.source_vn,
                           dest_vn=self.dest_vn,
                           source_port=self.source_port,
                           dest_port=self.dest_port,
                           protocol=self.protocol
                           )

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Flow', add_help=True)
    parser.add_argument('--source_ip', help='Source IP of the flow', required=True)
    parser.add_argument('--dest_ip', help='Destination IP of the flow', default='')
    parser.add_argument('--source_vn', help='VN of the source IP', default='')
#    parser.add_argument('--source_vrf', help='VRF of the source IP', default='')
    parser.add_argument('--dest_vn', help='VN of the destination IP', default='')
#    parser.add_argument('--dest_vrf', help='VRF of the destination IP', default='')
    parser.add_argument('--protocol', help='L3 Protocol of the flow', default='')
    parser.add_argument('--source_port', help='Source Port of the flow', default='')
    parser.add_argument('--dest_port', help='Destination Port of the flow', default='')
    parser.add_argument('--source_ip_type', help='source ip type', default='instance-ip')
    parser.add_argument('--dest_ip_type', help='dest ip type', default='instance-ip')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFlow = debugVertexFlow(**args)
    vertexPrint(vFlow).convert_json()
   #context = vIIP.get_context()
    #vertexPrint(context, detail=args.detail)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
