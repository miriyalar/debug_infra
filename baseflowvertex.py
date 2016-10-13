#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
This is non config vertex for base flow or session. Checkes the flow from the given vrouters
Agent/Kernel flow info will be collected
Input:
   Mandatory: 3 tuple, vrouters
   Optional: Rest of the 7 tuple
Dependant vertexes:
   Route
"""
import sys
import argparse
from collections import defaultdict
from logger import logger
from parser import ArgumentParser
from debugip import debugVertexIP
from vertex_print import vertexPrint
from utils import DictDiffer
from basevertex import get_logger, baseVertex
from contrailnode_api import Vrouter
import time
import debugroute

class baseFlowVertex(baseVertex):
    vertex_type = 'session'
    non_config_obj = True
    def __init__(self, source_ip, dest_ip, source_vrf,
                 dest_vrf, vrouters, **kwargs):
        self.dependant_vertexes = []#[debugroute.debugVertexRoute]
        self.source_ip = source_ip
        self.source_vrf = source_vrf
        self.dest_vrf = dest_vrf
        self.dest_ip = dest_ip
        self.vrouters = vrouters
        self.source_nip = kwargs.pop('source_nip', None)
        self.dest_nip = kwargs.pop('dest_nip', None)
        self.source_nvrf = kwargs.pop('source_nvrf', None)
        self.dest_nvrf = kwargs.pop('dest_nvrf', None)
        self.protocol = kwargs.pop('protocol', None)
        self.source_port = kwargs.pop('source_port', None)
        self.dest_port = kwargs.pop('dest_port', None)
        self.src_vn_fqname = kwargs.pop('source_vn', None)
        self.dest_vn_fqname = kwargs.pop('dest_vn', None)
        self.src_vn_fqname = self.src_vn_fqname or self.source_vrf[:self.source_vrf.rfind(':'):]
        self.dest_vn_fqname = self.dest_vn_fqname or self.dest_vrf[:self.dest_vrf.rfind(':'):]
        self.src_nvn_fqname = self.source_nvrf and self.source_nvrf[:self.source_vrf.rfind(':'):]
        self.dest_nvn_fqname = self.dest_nvrf and self.dest_nvrf[:self.dest_vrf.rfind(':'):]
        self.match_kv = {'dummy': 'dummy'}
        super(baseFlowVertex, self).__init__(**kwargs)

    def get_schema(self):
        pass

    def get_uuid(self):
        key = ['session', self.source_ip, self.dest_ip,
               self.source_vrf, self.source_nvrf,
               self.dest_vrf, self.dest_nvrf,
               self.source_port, self.dest_port, self.protocol] +\
               list(self.source_nip or [None]) + list(self.dest_nip or [None]) +\
               [vrouter['hostname'] for vrouter in self.vrouters]
        uuid = ':'.join(['' if val is None else val for val in key])
        return uuid

    def locate_obj(self):
        objs = list()
        objs.append({self.vertex_type: {'uuid': self.get_uuid(),
                                        'prefix': self.dest_ip,
                                        'ri_fqname': self.dest_vrf,
                                        'vrouters': self.vrouters}})
        return objs

    def store_config(self, vertex):
        pass

    def get_vrouter_info(self, vertex):
        return Vrouter(self.vrouters)

    def process_self(self, vertex):
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex)
        self._add_agent_to_context(vertex, agent)
        control = {}
        control['oper'] = {}
        self._add_control_to_context(vertex, control)

    def get_element(self, vertex, vrf_name, prefix):
        element = self._create_element(vertex, prefix=prefix,
                                       vrouters=self.get_vrouters(vertex),
                                       ri_fqname=vrf_name)
        return element

    def _get_agent_oper_db(self, introspect, vertex):
        oper = defaultdict(list)
        # Check Agent FlowTable
        oper['flow'] = self.check_flowtable(introspect, vertex)
        flow_ids = [flow['flow_handle'] for flow in oper['flow']['fwdflow'] + oper['flow']['revflow']]
        # Check Vrouter Kernel FlowTable
        oper['kflow'] = self.check_kflowtable(introspect, vertex, flow_ids)
        # Check Dropstats
        oper['dropstats'] = self.check_dropstats(introspect, vertex)
        # Check Route Tables
        for flow in oper['flow']['fwdflow'] + oper['flow']['revflow']:
            vrf_fqname = introspect.get_vrf_fqname(vrf_index=flow['dest_vrf'])
            debugroute.debugVertexRoute(context=self.context,
                                        element=self.get_element(vertex,
                                                                 vrf_fqname, prefix=flow['dip']))
            oper['routes'].append(debugroute.get_route_uuid(prefix=flow['dip'],
                                             ri_fqname=vrf_fqname,
                                             vrouters=self.get_vrouters(vertex)))
        return oper

    def check_kflowtable(self, introspect, vertex, flow_ids):
        self.src_vrf_id = introspect.get_vrf_id(self.source_vrf)
        self.dest_vrf_id = introspect.get_vrf_id(self.dest_vrf)
        flows = introspect.get_matching_kflows(self.source_ip, self.dest_ip,
                                             self.protocol, self.source_port,
                                             self.dest_port, self.source_nip,
                                             self.dest_nip, self.src_vrf_id,
                                             self.dest_vrf_id, flow_ids=flow_ids)
        if flows:
            self.logger.info('Kernel(%s): Found matching %s flow, sip %s and dip %s ' % (introspect._ip, len(flows), 
                                                                                         self.source_ip, self.dest_ip))
            for flow in flows:
                self.logger.info('5 tuple %s:%s %s:%s %s, Action: %s, Flags: %s' % \
                                 (flow.get('sip'), flow.get('sport'), flow.get('dip'),
                                  flow.get('dport'), flow.get('proto'), 
                                  flow.get('action'), flow.get('flags')))
                
        else:
            self.logger.info('Kernel(%s): Unable to find matching flow for sip/port %s/%s, dip/port %s/%s, protocol %s, snip %s, dnip %s, svn %s, dvn %s' % \
                             (introspect._ip, self.source_ip, self.source_port, self.dest_ip, self.dest_port, self.protocol,
                              self.source_nip, self.dest_nip,
                              self.src_vn_fqname, self.dest_vn_fqname))
        return flows

    def check_flowtable(self, introspect, vertex):
        flows = list()
        self.src_vrf_id = introspect.get_vrf_id(self.source_vrf)
        self.dest_vrf_id = introspect.get_vrf_id(self.dest_vrf)
        flow = introspect.get_matching_flows(self.source_ip, self.dest_ip,
                                             self.protocol, self.source_port,
                                             self.dest_port, self.src_vn_fqname,
                                             self.dest_vn_fqname, self.source_nip,
                                             self.dest_nip, self.src_nvn_fqname, self.dest_nvn_fqname,
                                             self.src_vrf_id, self.dest_vrf_id)
        if flow:
            self.logger.info('Agent(%s): Found matching %s flow, sip %s and dip %s ' % \
                             (introspect._ip, len(flow), 
                              self.source_ip, self.dest_ip))
            flows.extend(flow)
        else:
            self.logger.info('Agent(%s): Unable to find matching flow for sip/port %s/%s, dip/port %s/%s, protocol %s, snip %s, dnip %s, svn %s, dvn %s' % \
                             (introspect._ip, self.source_ip, self.source_port, self.dest_ip, self.dest_port, self.protocol, 
                              self.source_nip, self.dest_nip, self.src_vn_fqname, self.dest_vn_fqname))
        for flow in flows:
            self.logger.info('5 tuple %s:%s %s:%s %s, Action: %s' % \
                             (flow.get('sip'), flow.get('src_port'), 
                              flow.get('dip'), flow.get('dst_port'), 
                              flow.get('protocol'), flow.get('action_str')))
            if flow['sg_action_summary'][0]['action'] != 'pass':
                self.logger.warning('SG drop')
            if flow['action_str'][0]['action'] != 'pass':
                self.logger.warning('Flow action Drop')
        fwdflow = [flow for flow in flows if flow['reverse_flow'] == 'no']
        revflow = [flow for flow in flows if flow['reverse_flow'] == 'yes']
        return {'fwdflow': fwdflow, 'revflow': revflow}

    def check_dropstats(self, introspect, vertex):
        dropstats = defaultdict(dict)
        dropstats['src_initial'] = introspect.get_dropstats()
        initial = dropstats['src_initial']
        for i in range(2):
            time.sleep(5)
            current = introspect.get_dropstats()
            dropstats['src_diff_'+str(i)] = {key:current[key]
                                             for key in DictDiffer(current, initial).changed()}
            initial = current
        return dropstats

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Flow', add_help=True)
    #parser.add_argument('--source_ip', help='Source IP of the flow', required=True)
    #parser.add_argument('--dest_ip', help='Destination IP of the flow', required=True)
    #parser.add_argument('--source_vn', help='VN of the source IP')
    #parser.add_argument('--dest_vn', help='VN of the destination IP')
    #parser.add_argument('--protocol', help='L3 Protocol of the flow')
    #parser.add_argument('--source_port', help='Source Port of the flow')
    #parser.add_argument('--dest_port', help='Destination Port of the flow')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFlow = baseFlowVertex(source_ip='30.30.30.3',
                           vrouters=[{'hostname':'a3s19',
                                               'ip_address': '10.84.17.5',
                                               'sandesh_http_port': 8085}],
                           dest_ip='30.30.30.3',
                           source_vrf='default-domain:admin:testvn:testvn',
                           dest_vrf='default-domain:admin:testvn:testvn',
                           **args)
                           #config_ip='10.84.17.5',
                           #config_port='8082')
    vP = vertexPrint(vFlow)
    vP.convert_json()

