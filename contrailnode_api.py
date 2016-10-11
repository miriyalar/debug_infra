from introspect import ControllerIntrospect, AgentIntrospect, SchemaIntrospect
from contrail_api import ContrailApi
from contrail_uve import ContrailUVE

class ContrailNodes:
    def __init__(self, contrail_info):
        self.contrail_info = contrail_info
        self.config = []
        self.vrouter = []
        self.control = []

class AnalyticsNode:
    def __init__(self, analytics_nodes, port=None, token=None):
        self._analytics_nodes = analytics_nodes
        self._analytics_api = None
        self.token = token
        for node in analytics_nodes:
            self._analytics_api = ContrailUVE(ip=node['ip_address'],
                                              port=port or node['port'],
                                              token=self.token)
            break

    def get_object(self, category='uve', object_type=None, object_name=None, select_fields=[]):
        dobj = {}
        try:
            dobj = self._analytics_api.get_object(object_name, object_type, select_fields)
        except:
            pass
        return dobj

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

    def get_fqname_to_id(self, obj_type, fq_name):
        fq_name = fq_name.split(':') if ':' in fq_name else fq_name
        api = self.config_api[0]['obj']
        data = {'type': obj_type, 'fq_name': fq_name}
        response = api.post('fqname-to-id', data)
        return response['uuid']

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
                    ref_value = dobj.pop('ref', None)
                    uuid_obj = dobj.values()[0]['uuid']
                    hostname = capi['hostname']
                    if uuid_obj not in objs:
                        objs[uuid_obj] = {}
                    if hostname not in objs[uuid_obj]:
                        objs[uuid_obj][hostname] = {}
                    if ref_value:
                        dobj['ref'] = ref_value
                    objs[uuid_obj][hostname].update(dobj)
            except:
                pass
        return dobjs, objs


    def get_ip_type(self, ip_address=None, vn=None, 
                    config_ip=None, config_port=None):
        ip_type = None
        if config_ip and config_port:
            config_api = None
            for capi in self.config_api:
                if capi['ip_address'] == config_ip and \
                   capi['port'] == config_port:
                    config_api = [capi]
                    break
        else:
            config_api = self.config_api
        if not config_api or not vn or not ip_address:
            return ip_type
        try:
            capi = config_api[0]['obj']
            iobjs = capi.get_object_deep('virtual-network', 
                                         'instance_ip_back_refs.instance_ip_address', 
                                         where='fq_name=%s' % (vn))
            if ip_address in iobjs:
                return 'instance-ip'
            iobjs = capi.get_object_deep('virtual-network',
                                         'floating_ip_pools.floating_ips.floating_ip_address',
                                         where='fq_name=%s'%(vn))
            if ip_address in iobjs:
                return 'floating-ip'
        except Exception as e:
            print e
        return 'external'


class IntrospectNode(object):
    def __init__(self, nodes, _cls, port=None):
        self.nodes = nodes
        self.handles = dict()
        for node in self.nodes:
            port = port or node.get('sandesh_http_port')
            self.handles[node['ip_address']] = _cls(ip=node['ip_address'],
                                                    port=port)
    def get_nodes(self):
        return self.nodes

    def get_inspect_h(self, ip):
        return self.handles[ip]

class Vrouter(IntrospectNode):
    def __init__(self, vrouter_nodes, port=None):
        super(Vrouter, self).__init__(vrouter_nodes, AgentIntrospect, port=port)

class ControlNode(IntrospectNode):
    def __init__(self, control_nodes, port=None):
        super(ControlNode, self).__init__(control_nodes, ControllerIntrospect, port=port)

class SchemaNode(IntrospectNode):
    def __init__(self, config_nodes, port=None):
        super(SchemaNode, self).__init__(config_nodes, SchemaIntrospect, port=port)
        for node in config_nodes:
            inspect = super(SchemaNode, self).get_inspect_h(node['ip_address'])
            if not inspect.is_service_up():
                self.handles.pop(node['ip_address'], None)
            else:
                self.node = node
        if len(self.handles) == 0:
            print 'Schema Transformer is down'
        elif len(self.handles) > 1:
            print 'Multiple active Schema transformer processes'
        self.nodes = [self.node]

'''
class IntrospectNode:
    @staticmethod
    def introspect(url, nodes, ip=None, port=None, key=None):
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
'''
