#!/usr/bin/env python
#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#

import os
import json
from parser import ArgumentParser
from argparse import RawTextHelpFormatter
from keystone_auth import ContrailKeystoneAuth
from cluster_status import ClusterStatus

DEF_CONTRAIL_OUTPUT_JSON = 'contrail_debug_output.json'
DEF_CONTRAIL_LOG = 'debug_nodes.log'

class fileUtil():
    def __init__(self, filename=None):
        self.filename = filename or \
            os.path.dirname(os.path.realpath(__file__))+'/'+DEF_CONTRAIL_OUTPUT_JSON

    def open_file(self, filename):
        try:
            fh = open(filename, 'r')
        except IOError as e:
            print("({})".format(e))
            fh = None

class contrailOutputJson(object):
    def __init__(self, filename=None):
        self.filename = filename or \
            os.path.dirname(os.path.realpath(__file__))+'/'+DEF_CONTRAIL_OUTPUT_JSON
        self.output_json_dict = {
            'summary': 'get_summary_of_visited_vertexes',
            'vertexes': 'get_visited_vertexes',
            'alarms': 'get_alarms',
            'status': 'get_status'
        }

    def open_file(self, filename):
        try:
            fh = open(filename, 'r')
        except IOError as e:
            print("({})".format(e))
            fh = None
        return fh

    def get_output(self, arg_list):
        # Pra, rewrite
        if not arg_list:
            return self.get_summary_of_visited_vertexes()
        if 'summary' in arg_list:
            return self.get_summary_of_visited_vertexes()
        elif 'vertexes' in arg_list:
            node_types = arg_list[1:]
            return self.get_visited_vertexes(node_types=node_types)
        elif 'alarms' in arg_list:
            return self.get_alarms()
        elif 'status' in arg_list:
            status_args = arg_list[arg_list.index('status')+1:]
            return self.get_status(hosts=status_args)
        '''
        for arg in arg_list:
            func = self.output_json_dict.get(arg, None)
            if func in self.__class__.__dict__:
                if arg in 
                #func_ptr = self.__class__.__dict__.get(func, None)
                #ret_val = func_ptr(self, arg)
        '''
            
    def get_summary_of_visited_vertexes(self):
        fh = self.open_file(self.filename)
        if not fh:
            return []
        data = json.loads(fh.read())
        vertexes = data.get('summary_of_visited_vertexes', [])
        fh.close()
        return vertexes

    def get_visited_vertexes(self, node_types=[]):
        fh = self.open_file(self.filename)
        if not fh:
            return []
        data = json.loads(fh.read())
        fh.close()
        visited_vertexes = data.get('visited_vertexes', {})
        if not node_types:
            return visited_vertexes
        if isinstance(node_types, basestring):
            node_types = node_types.split()
        vertexes = {}
        for ntype in node_types:
            vertexes[ntype] = visited_vertexes.get(ntype, [])
        return vertexes
    
    def get_alarms(self):
        fh = self.open_file(self.filename)
        if not fh:
            return []
        data = json.loads(fh.read())
        alarms = data.get('alarm_status', {})
        fh.close()
        return alarms

    def get_host_status(self, hostname=None):
        fh = self.open_file(self.filename)
        if not fh:
            return []
        data = json.loads(fh.read())
        host_status = data.get('host_status', {})
        if not hostname:
            fh.close()
            return host_status
        status = host_status.get(hostname, {})
        fh.close()
        return status


class contrailLog(object):
    def __init__(self, filename=None):
        self.filename = filename or \
            os.path.dirname(os.path.realpath(__file__))+'/'+DEF_CONTRAIL_LOG

    def open_file(self, filename):
        try:
            fh = open(filename, 'r')
        except IOError as e:
            print("({})".format(e))
            fh = None
        return fh

    def get_logs(self, log_type=['INFO']):
       fh =  self.open_file(self.filename)
       data = fh.read()
       lines = data.split('\n')
       fh.close()
       log_type = log_type or ['INFO', 'DEBUG', 'ERROR']
       log_type = [t.upper() if t in ['info', 'debug', 'error'] else t for t in log_type] 
       type_set = set(log_type)
       return [li for li in lines if li and set(li.split()).intersection(type_set)]

class Status(object):
    def __init__(self):
        parser = ArgumentParser(description='cluster status', 
                                add_help=True, 
                                formatter_class=RawTextHelpFormatter)
        self.args = []
        self.args = parser.parse_args(self.args)

    def get_status(self, uuid_type=None, uuid=None, hosts=None):
        self.keystone = ContrailKeystoneAuth(auth_ip=self.args.get('auth_ip'),
                                             auth_port=self.args.get('auth_port'),
                                             auth_url_path=self.args.get('auth_url_path'),
                                             admin_username=self.args.get('username'),
                                             admin_password=self.args.get('password'),
                                             admin_tenant_name=self.args.get('tenant'))
        resp = self.keystone.authenticate()
        if resp.has_key('access'):
            self._token = resp['access']['token']['id']
        self.vrouters = hosts
        (c_status, h_status, a_status) = ClusterStatus(token=self._token,
                        config_ip=self.args.get('config_ip'),
                        config_port=self.args.get('config_port'),
                        analytics_ip=self.args.get('analytics_ip'),
                        analytics_port=self.args.get('analytics_port')).get(uuid=uuid, uuid_type=uuid_type,
                                                                            vrouters=self.vrouters)
        status = dict()
        status['cluster_status'] = c_status
        status['host_status'] = h_status
        status['alarm_status'] = a_status
        self._status = status
        return status


if __name__ == "__main__":
    import pdb; pdb.set_trace()
    cs = Status()
    status = cs.get_status(hosts=['a3s19'])
    import pdb; pdb.set_trace()
    print json.dumps(status.get('alarm_status'), indent=4)
    print json.dumps(status.get('cluster_status'), indent=4)
    print json.dumps(status.get('host_status'), indent=4)
    oj  = contrailOutputJson()
    import pdb; pdb.set_trace()
    print json.dumps(oj.get_summary_of_visited_vertexes(), indent=4)
    print json.dumps(oj.get_alarms(), indent=4)
    print json.dumps(oj.get_host_status(), indent=4)
    dt = contrailLog()
    print json.dumps(dt.get_logs(log_type=None), indent=4)
    print json.dumps(dt.get_logs(log_type=['INFO']), indent=4)
    print json.dumps(dt.get_logs(log_type=['INFO', 'ERROR']), indent=4)
    print json.dumps(dt.get_logs(log_type=['INFO', 'DEBUG']), indent=4)

            
