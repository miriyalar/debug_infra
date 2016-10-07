#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
"""
A context is maintained for debugging session via debug vertex
Context maintains visisted vertexes and their objects
Context code also authenticates with keystone to access config/analytics nodes
Cluster status also maintained at the context.
"""
from keystone_auth import ContrailKeystoneAuth
from contrailnode_api import ControlNode, ConfigNode, Vrouter, AnalyticsNode, SchemaNode
from contrail_utils import ContrailUtils
from cluster_status import ClusterStatus

class Context(object):
    def __init__(self, vertex_type, **kwargs):
        self.path = list()
        self.visited_vertexes_inorder = list()
        self.debugged_vertex = vertex_type
        self.vrouters = set()
        self.config_ip = kwargs.get('config_ip')
        self.config_port = kwargs.get('config_port')
        self.auth_ip = kwargs.get('auth_ip')
        self.auth_port = kwargs.get('auth_port')
        self.auth_url_path = kwargs.get('auth_url_path')
        self.admin_password = kwargs.get('password')
        self.admin_username = kwargs.get('username')
        self.admin_tenant_name = kwargs.get('tenant')
        self.analytics_ip = kwargs.get('analytics_ip', None)
        self.analytics_port = kwargs.get('analytics_port', None)
        self.control_port = kwargs.get('control_port', None)
        self.agent_port = kwargs.get('agent_port', None)
        self.schema_transformer_port = kwargs.get('schema_transformer_port', None)
        self.depth = kwargs.get('depth', -1)
        self._token = kwargs.get('token', None)
        self.config_api = None
        self.contrail = dict()
        self.uuid_to_vertex = dict()

    @property
    def token(self):
        if not getattr(self, '_token', None):
            self.keystone = ContrailKeystoneAuth(auth_ip=self.auth_ip,
                                    auth_port=self.auth_port,
                                    auth_url_path=self.auth_url_path,
                                    admin_username=self.admin_username,
                                    admin_password=self.admin_password,
                                    admin_tenant_name=self.admin_tenant_name)
            resp = self.keystone.authenticate()
            if resp.has_key('access'):
                self._token = resp['access']['token']['id']
        return self._token

    @property
    def connections(self):
        if not getattr(self, '_connections', None):
            self._connections = ContrailUtils(
                                    token=self.token).get_control_nodes(
                                    self.config_ip, self.config_port)
        return self._connections

    @property
    def config(self):
        if not getattr(self, '_config', None):
            self._config = ConfigNode(self.connections['config_nodes'],
                                      token=self.token)
        return self._config

    @property
    def control(self):
        if not getattr(self, '_control', None):
            self._control = ControlNode(self.connections['control_nodes'], port=self.control_port)
        return self._control

    @property
    def analytics(self):
        if not getattr(self, '_analytics', None):
            if self.analytics_ip:
                analytics_nodes = [{'ip_address': self.analytics_ip,
                                   'host_name': '',
                                   'port': self.analytics_port}]
            else:
                analytics_nodes = self.connections['analytics_nodes']
            self._analytics = AnalyticsNode(analytics_nodes,
                                            port=self.analytics_port,
                                            token=self.token)
        return self._analytics

    @property
    def schema(self):
        if not getattr(self, '_schema', None):
            self._schema = SchemaNode(self.connections['config_nodes'], port=self.schema_transformer_port)
        return self._schema

    @property
    def status(self):
        if not getattr(self, '_status', None):
            (c_status, h_status, a_status) = ClusterStatus(token=self.token,
                                                           config_ip=self.config_ip,
                                                           config_port=self.config_port,
                                                           analytics_ip=self.analytics_ip,
                                                           analytics_port=self.analytics_port).get(vrouters=self.vrouters)
            status = dict()
            status['cluster_status'] = c_status
            status['host_status'] = h_status
            status['alarm_status'] = a_status
            self._status = status
        return self._status

    def get_cluster_status(self):
        return self.status.get('cluster_status', None)

    def get_cluster_alarm_status(self):
        return self.status.get('alarm_status', None)

    def get_cluster_host_status(self):
        return self.status.get('host_status', None)

    def get_debugged_vertex(self):
        return self.debugged_vertex

    def get_path(self):
        return self.path

    def add_path(self, element):
        self.path.append(element)

    def delete_path(self, element):
        self.path.remove(element)

    def is_visited_vertex(self, uuid):
        if uuid in self.uuid_to_vertex.keys():
            return True
        return False

    def get_visited_vertices(self):
        return self.visited_vertexes_inorder

    def _map_uuid_to_vertex(self, vertex):
        self.uuid_to_vertex.update({vertex['uuid']: vertex})

    def add_vertex(self, vertex):
        vertex_summary = {'vertex_type': vertex['vertex_type'],
                          'uuid': vertex['uuid'],
                          'fq_name': vertex.get('fq_name'),
                          'display_name': vertex.get('display_name'),
                          }
        self.visited_vertexes_inorder.append(vertex_summary)
        self._map_uuid_to_vertex(vertex)

    def add_vrouter(self, nodes, vertex_type, uuid, fq_name):
        for node in nodes or []:
            hostname = node.get('hostname', None)
            if hostname:
                self.vrouters.add(hostname)

    def get_vrouters(self):
        return self.vrouters

    def get_vertex_of_uuid(self, uuid):
        return self.uuid_to_vertex[uuid]

    def get_uuid_of_fqname(self, fq_name, vertex_type):
        for vertex in self.visited_vertexes_inorder:
            if vertex['fq_name'] == fq_name and \
               vertex['vertex_type'] == vertex_type:
                return vertex['uuid']

    def get_vertex_of_fqname(self, fq_name, vertex_type):
        uuid = self.get_uuid_of_fqname(fq_name, vertex_type)
        return self.get_vertex_of_uuid(uuid)

    def get_control_inspect_h(self):
        inspect_h = list()
        for node in self.control.get_nodes():
            inspect_h.append((node['hostname'], self.control.get_inspect_h(node['ip_address'])))
        return inspect_h
