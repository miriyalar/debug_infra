from introspect import Introspect
from contrail_api import ContrailApi
from contrail_uve import ContrailUVE

class ContrailNodes:
    def __init__(self, contrail_info):
        self.contrail_info = contrail_info
        self.config = []
        self.vrouter = []
        self.control = []

class AnalyticsNode:
    def __init__(self, analytics_nodes):
        self._analytics_nodes = analytics_nodes
        self._analytics_api = None
        for node in analytics_nodes:
            self._analytics_api = ContrailUVE(ip=node['ip_address'], port=node['port'])
            break
    
    def get_object(self, category='uve', object_type=None, object_name=None, select_fields=[]):
        return self._analytics_api.get_object(object_name, object_type, select_fields)

class ConfigNode:
    def __init__(self, config_nodes, token=None):
        self.config_nodes = config_nodes
        self.token = token
        self.config_api = []
        self.update_config_nodes(config_nodes)

    def update_config_nodes(self, config_nodes):
        for node in config_nodes:
            if not any(n['ip_address'] == node['ip_address'] for n in self.config_api):
                capi = {}
                capi['ip_address'] = node['ip_address']
                capi['port'] = node['port']
                capi['hostname'] = node['hostname']
                capi['obj'] = ContrailApi(ip=capi['ip_address'], port=capi['port'], token=self.token)
                self.config_api.append(capi)

    def get_object(self, object_type, config_ip=None, config_port=None, 
                   schema_to_use='', where=''):
        objs = {}
        dobjs = []
        if config_ip and config_port:
            for capi in self.config_api:
                if capi['ip_address'] == config_ip and \
                   capi['port'] == config_port:
                    config_api = [capi]
                    break
        else:
            config_api = self.config_api
        for capi in config_api:
            try:
                dobjs = capi['obj'].get_object_deep(object_type, 
                                                    schema_to_use, 
                                                    where=where)
                
                for dobj in dobjs:
                    uuid_obj = dobj.values()[0]['uuid']
                    hostname = capi['hostname']
                    if uuid_obj not in objs:
                        objs[uuid_obj] = {}
                    if hostname not in objs[uuid_obj]:
                        objs[uuid_obj][hostname] = {}
                    objs[uuid_obj][hostname].update(dobj)
            except:
                pass
        return dobjs, objs
                
class Vrouter:
    def __init__(self, vrouter_nodes):
        self.vrouter_nodes = vrouter_nodes
    def get_nodes(self):
        return self.vrouter_nodes
    def introspect(self, url, ip=None, port=None, key=None):
        return IntrospectNode.introspect(url, 'vrouter_', self.vrouter_nodes,
                        ip, port, key)

class ControlNode:
    def __init__(self, control_nodes):
        self.control_nodes = control_nodes
    def get_nodes(self):
        return self.control_nodes
    def introspect(self, url, ip=None, port=None, key=None):
        return IntrospectNode.introspect(url, 'control_node_', self.control_nodes,
                               ip, port, key)

class IntrospectNode:
    @staticmethod
    def introspect(url, node_type, nodes, ip=None, port=None, key=None):
        ispect = {}
        if ip and port:
            nodes = [{'ip_address': ip,'sandesh_http_port': port, 'hostname':None}]
        for node in nodes:
            ip = node['ip_address']
            hostname = node['hostname']
            port = node['sandesh_http_port']
            base_url = 'http://%s:%s/' % (ip, port)
            url_dict_resp = Introspect(url=base_url+url).get()
            if not hostname:
                return url_dict_resp
            ispect[hostname] = {}
            if key:
                ispect[hostname][key] = url_dict_resp
            else:
                ispect[hostname] = url_dict_resp
        #Utils.merge_dict(
        return ispect
