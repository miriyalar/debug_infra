import sys
import argparse
from collections import defaultdict
from logger import logger
from parser import ArgumentParser
from debugip import debugVertexIP
from vertex_print import vertexPrint
from utils import DictDiffer
from basevertex import get_logger, create_vertex, baseVertex
from contrailnode_api import Vrouter
from context import Context
import time


class baseFlowVertex(baseVertex):
    vertex_type = 'session'
    non_config_obj = True
    def __init__(self, source_ip, dest_ip, source_vrf,
                 dest_vrf, vrouters, **kwargs):
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
        objs.append({self.vertex_type: {'uuid': self.get_uuid()}})
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

    def _get_agent_oper_db(self, introspect, vertex):
        oper = {}
        oper['route'] = self.check_routes(introspect, vertex)
        oper['flow'] = self.check_flowtable(introspect, vertex)
        oper['dropstats'] = self.check_dropstats(introspect, vertex)
        return oper
        

    def check_routes(self, introspect, vertex):
        return {}
        '''
        oper = defaultdict(dict)
        for vrouter in self.svrouter.get_nodes():
            introspect = self.svrouter.get_inspect_h(vrouter['ip_address'])
            hostname = vrouter['hostname']
            (check, route) = introspect.is_route_exists(self.source_vrf, self.dest_ip)
            if not check:
                print 'route for destip %s doesnt exist in source vrf %s'%(self.dest_ip, self.source_vrf)
            print 'route exists for destip %s in source vrf %s'%(self.dest_ip, self.source_vrf)
            oper['src_route'][hostname] = route

        for vrouter in self.dvrouter.get_nodes():
            introspect = self.dvrouter.get_inspect_h(vrouter['ip_address'])
            hostname = vrouter['hostname']
            (check, route) = introspect.is_route_exists(self.dest_vrf, self.source_ip)
            if not check:
                print 'route for srcip %s doesnt exist in dest vrf %s'%(self.source_ip, self.dest_vrf)
            print 'route exists for srcip %s in dest vrf %s'%(self.source_ip, self.dest_vrf)
            oper['dst_route'][hostname] = route
        self.vertex['agent']['oper'].update(oper)
        '''
        pass

    def check_flowtable(self, introspect, vertex):
        flows = list()
        src_vrf_id = introspect.get_vrf_id(self.source_vrf)
        dest_vrf_id = introspect.get_vrf_id(self.dest_vrf)
        flow = introspect.get_matching_flows(self.source_ip, self.dest_ip,
                                             self.protocol, self.source_port,
                                             self.dest_port, self.src_vn_fqname,
                                             self.dest_vn_fqname, self.source_nip,
                                             self.dest_nip, self.src_nvn_fqname, self.dest_nvn_fqname,
                                             src_vrf_id, dest_vrf_id)
        if flow:
            print 'Found matching %s flow on agent %s, sip %s and dip %s ' % (len(flow), introspect._ip, 
                                                                              self.source_ip, self.dest_ip)
            flows.extend(flow)
        else:
            print 'Unable to find matching flow on agent %s for sip %s, dip %s, snip %s, dnip %s, svn %s, dvn %s' % \
                (introspect._ip, self.source_ip, self.dest_ip, self.source_nip, self.dest_nip, \
                 self.src_vn_fqname, self.dest_vn_fqname)
        for flow in flows:
            if flow['sg_action_summary'][0]['action'] != 'pass':
                print 'SG drop'
            if flow['action_str'][0]['action'] != 'pass':
                print 'Flow action Drop'
        return flows


    def check_dropstats(self, introspect, vertex):
        dropstats = defaultdict(dict)
        dropstats['src_initial'] = introspect.get_dropstats()
        for i in range(2):
            time.sleep(5)
            current = introspect.get_dropstats()
            initial = dropstats['src_initial']
            dropstats['src_diff_'+str(i)] = {key:current[key]
                                             for key in DictDiffer(current, initial).changed()}
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

