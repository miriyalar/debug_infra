#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
Contrail cluster status, also takes uuid of an object and gets the status of relevant compute nodes
"""

from contrail_utils import ContrailUtils
from contrail_uve import ContrailUVE
from collections import defaultdict
from utils import Utils

class ClusterStatus(object):
    def __init__(self, config_ip='127.0.0.1', config_port='8082', 
                 analytics_ip=None, analytics_port=None, config_api=None, token=None):
        self.token = token
        self.config_ip = config_ip
        self.config_port = config_port
        self.config_api = config_api
        self.analytics_ip = analytics_ip
        self.analytics_port = analytics_port
    
    def get(self, uuid_type=None, uuid=None, vrouters=None):
        contrail_status = defaultdict(dict)
        host_status = defaultdict(dict)
        alarm_status = defaultdict(dict)
        contrail = ContrailUtils(token=self.token).get_contrail(self.config_ip, self.config_port, 
                                                                uuid_type=uuid_type, uuid=uuid)
        analytics_ip = self.analytics_ip or Utils.get_debug_ip(hostname=contrail['control']['analytics_nodes'][0]['hostname'],
                                                               ip_address=contrail['control']['analytics_nodes'][0]['ip_address'])
        analytics_port = self.analytics_port or contrail['control']['analytics_nodes'][0]['port']
        uve = ContrailUVE(ip=analytics_ip, port=analytics_port, token=self.token)
        for node_type, node_list  in contrail['control'].iteritems():
            #contrail_status['control'][node_type] = list()
            contrail_status[node_type] = list()
            for node in node_list:
                hostname = node['hostname']
                node_status = uve.get_object(hostname, node_type.replace('_', '-')[:-1], 
                                             select_fields=['NodeStatus.process_status', 'UVEAlarms'], 
                                             found_error=False)
                contrail_status[node_type].append(node_status)
                host_status[hostname][node_type.replace('_', '-')[:-1]] = node_status
                if node_status.get('UVEAlarms', None):
                    alarm_status[hostname][node_type.replace('_', '-')[:-1]] = node_status['UVEAlarms']

        contrail_status['vrouter'] = list()
        if not vrouters:
            vrouters = [node['hostname'] for node in contrail['vrouter']]
        for hostname in vrouters:
            node_type = 'vrouter'
            node_status = uve.get_object(hostname, node_type, 
                                         select_fields=['NodeStatus.process_status', 'VrouterAgent.xmpp_peer_list',
                                                        'VrouterAgent.control_ip','UVEAlarms'], 
                                         found_error=False)
            contrail_status['vrouter'].append(node_status)
            host_status[hostname][node_type] = node_status
            if node_status.get('UVEAlarms', None):
                alarm_status[hostname][node_type] = node_status['UVEAlarms']

        return contrail_status, host_status, alarm_status

if __name__ == '__main__':
    cluster_status, host_status, alarm_status = ClusterStatus(config_ip='10.84.17.5', config_port='8082').get()
    import pdb; pdb.set_trace()
    cluster_status, host_status, alarm_status = ClusterStatus(config_ip='10.84.17.5', config_port='8082').get(uuid_type='virtual-machine-interface', uuid='060c2b5f-d43a-4ea5-844d-393819ff36fd')
    
        

    
