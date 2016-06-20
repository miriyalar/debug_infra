import pdb
from logger import logger
from introspect import Introspect
from contrail_utils import ContrailUtils
from utils import Utils
from vertex_print import vertexPrint
from collections import OrderedDict, defaultdict
from contrailnode_api import ControlNode, ConfigNode, Vrouter, AnalyticsNode
from keystone_auth import ContrailKeystoneAuth
from abc import ABCMeta, abstractmethod
import ConfigParser
import sys
import os

def get_keystone_auth_token(**kwargs):
    token = None
    keystone_obj = ContrailKeystoneAuth(auth_ip=kwargs.get('auth_ip'),
                                        auth_port=kwargs.get('auth_port'),
                                        auth_url_path=kwargs.get('auth_url_path'),
                                        admin_username=kwargs.get('username'),
                                        admin_password=kwargs.get('password'),
                                        admin_tenant_name=kwargs.get('tenant'))
    resp = keystone_obj.authenticate()
    if resp.has_key('access'):
        return resp['access']['token']['id']
    return token

def create_global_context(**kwargs):
    gcontext = {}
    gcontext['path'] = []
    gcontext['visited_vertexes'] = {}
    gcontext['vertexes'] = defaultdict(list)
    gcontext['visited_nodes'] = {}
    gcontext['visited_vertexes_inorder'] = []
    gcontext['config_api'] = None
    gcontext['config_ip'] = kwargs.get('config_ip')
    gcontext['config_port'] = kwargs.get('config_port')
    gcontext['contrail'] = {}
    gcontext['token'] = get_keystone_auth_token(**kwargs)
    return gcontext

class baseVertex(object):
    '''Abstract Base Class for Vertex'''
    __metaclass__ = ABCMeta
    def __init__(self, context=None, **kwargs):
        self.config = None
        self.control = None
        self.analytics = None
        self.vrouter = None
        self.config_objs = {}
        if not context:
            self.context = create_global_context(**kwargs)
        else:
            self.context = context
        if self._is_vertex_type_exists_in_path(self.vertex_type):
            return
        self.element = kwargs.get('element', None)
        self.uuid = kwargs.get('uuid', None)
        self.fq_name = kwargs.get('fq_name', None)
        self.display_name = kwargs.get('display_name', None)
        self.config_ip = kwargs.get('config_ip', self.context.get('config_ip'))
        self.config_port = kwargs.get('config_port', self.context.get('config_port'))
        self.obj_type = kwargs.get('obj_type', None) or self.vertex_type
        self.logger = logger(logger_name=self.get_class_name()).get_logger()
        self.token = self.context['token']
        if not self.token:
            self.logger.warn('Authentication failed: Unable to fetch token from keystone')
        self._set_contrail_control_objs(self.context)
        self.schema = self.get_schema()
        if not self.element:
            if not hasattr(self, 'match_kv') or not any(self.match_kv.itervalues()):
                self.match_kv = {'uuid': self.uuid, 'fq_name': self.fq_name,
                                 'display_name': self.display_name}
            if not any(self.match_kv.itervalues()):
                raise Exception('Nothing to match, please check match args')
        self.process_vertexes(self._locate_obj())

    @abstractmethod
    def process_self(self, vertex_type, uuid, vertex):
        pass

    @abstractmethod
    def get_schema(self, context, **kwargs):
        pass

    def _set_contrail_control_objs(self, context):
        self.config = context['contrail'].get('config', None)
        self.control = context['contrail'].get('control', None)
        self.analytics = context['contrail'].get('analytics', None)
        if not self.config:
            contrail_control = ContrailUtils(token=self.token).get_control_nodes(self.config_ip, self.config_port)
            self.context['contrail']['config'] = self.config = ConfigNode(contrail_control['config_nodes'], token=self.token)
            self.context['contrail']['control'] = self.control = ControlNode(contrail_control['control_nodes'])
            self.context['contrail']['analytics'] = self.analytics = AnalyticsNode(contrail_control['analytics_nodes'])
            self.context['config_ip'] = self.config_ip
            self.context['config_port'] = self.config_port

    def _set_contrail_vrouter_objs(self, vertex_type, obj):
        contrail_info = ContrailUtils(token=self.token).get_contrail_info(
                                                        obj[vertex_type]['uuid'],
                                                        vertex_type,
                                                        config_ip=self.config_ip,
                                                        config_port=self.config_port,
                                                        context_path=self.context['path'],
                                                        fq_name=obj[vertex_type]['fq_name'])
        self.vrouter = Vrouter(contrail_info['vrouter'])

    def get_context(self):
        return self.context

    def get_context_path(self):
        return self.context['path']

    def get_class_name(self):
        return self.__class__.__name__

    def process_vertexes(self, objs):
        vertex_type = self.vertex_type
        for obj in objs:
            uuid = obj[vertex_type]['uuid']
            fq_name = ':'.join(obj[vertex_type]['fq_name'])
            if self._is_visited_vertex(uuid):
                continue
            self._set_contrail_vrouter_objs(vertex_type, obj)
            self._store_vertex(vertex_type, uuid, obj)
            self._store_config(vertex_type, uuid, obj, self.config_objs)
            self._store_control_config(vertex_type, obj)
            self._store_analytics_uves(vertex_type, uuid, fq_name, obj)
            self._store_agent_config(vertex_type, obj)
            self.process_self(vertex_type, uuid, obj)
            self._process_dependants(vertex_type, uuid, fq_name, self.dependant_vertexes)

    def _add_to_context_path(self, element):
        if not self.context:
            self.context = {}
            self.context['path'] = []
        self.current_frame = element
        self.context['path'].append(element)
        self.logger.debug('Add '+ str(self.get_context_path()))

    def _remove_from_context_path(self, element):
        self.context['path'].remove(element)
        self.logger.debug('Remove' + str(self.get_context_path()))

    def _process_dependants(self, vertex_type, uuid, fq_name, dependant_vertexes):
        from debugvm import debugVertexVM
        from debugvn import debugVertexVN
        from debugvmi import debugVertexVMI
        from debugsg import debugVertexSG
        from debugip import debugVertexIP
        from debugfip import debugVertexFIP
        element = self._create_element(vertex_type=vertex_type,
                                       uuid=uuid,
                                       fq_name=fq_name)
        for dependant_vertex in dependant_vertexes:
            self._add_to_context_path(element)
            eval(dependant_vertex)(context=self.context, element=element)
            self._remove_from_context_path(element)

    def _create_vertex(self, vertex_type, uuid, fq_name=None):
        vertex = {
            'uuid': uuid,
            'fq_name': fq_name,
            'vertex_type': vertex_type,
            'config': {},
            'agent' : {},
            'control': {},
            'analytics': {'uve':{}},
        }
        return vertex

    def _store_vertex(self, vertex_type, uuid, config_obj):
        fq_name = ':'.join(config_obj[vertex_type]['fq_name'])
        vertex = self._create_vertex(vertex_type, uuid, fq_name)
        self.context['vertexes'][vertex_type].append(vertex)
        self.context['visited_vertexes'][uuid] = vertex
        self.context['visited_nodes'][vertex_type + ', ' + fq_name] = vertex
        visited_vertexes_inorder = {'uuid': config_obj[vertex_type]['uuid'],
                                 'fq_name': fq_name,
                                 'display_name': config_obj[vertex_type]['display_name'],
                                 'vertex_type': vertex_type}
        self.context['visited_vertexes_inorder'].append(visited_vertexes_inorder)

    def _is_visited_vertex(self, uuid):
        if self.context:
            return uuid in self.context['visited_vertexes']
        else:
            return False

    def _is_vertex_type_exists_in_path(self, vertex_type):
        for element in self.context['path']:
            if element['type'] == vertex_type:
                return True
        return False

    def _create_element(self, vertex_type, uuid, fq_name):
        element = {}
        element['type'] = vertex_type
        element['uuid'] = uuid
        element['fq_name'] = fq_name
        return element

    def get_class(self):
        return self.__class__.__name__

    def _locate_obj(self):
        input_dict = {'match_dict': {}}
        if self.element != None:
            element_type = self.element['type']
            element_uuid = self.element['uuid']
            input_dict = {"type": element_type,
                          "match_dict" : {'uuid': element_uuid} }
        else:
            input_dict['type'] = self.obj_type
            for key,value in self.match_kv.iteritems():
                #if key == 'obj_type':
                #    input_dict['type'] = value
                #else:
                    if value:
                        input_dict['match_dict'][key] = value
                        #for now just one match
                        break
        object_type = input_dict['type']
        key, value = input_dict['match_dict'].popitem()
        try:
            schema_to_use = self.schema[object_type][key]
        except KeyError:
            schema_to_use = None
        where = '%s==%s' % (key, value)
        ret_obj_list, self.config_objs = self.config.get_object(object_type,
                                                  schema_to_use=schema_to_use,
                                                  where=where)
        return ret_obj_list

    def _store_config(self, vertex_type, uuid, obj, config_objs):
        cobj = config_objs.get(uuid, None)
        if cobj:
            self.context['visited_vertexes'][uuid]['config'].update(cobj)

    def _store_control_config(self, vertex_type, obj):
        url_str = 'Snh_IFMapTableShowReq?table_name=&search_string='
        uuid = obj[vertex_type]['uuid']
        url_str += '%s' % (':'.join(obj[vertex_type]['fq_name']))
        iobjs = self.control.introspect(url_str, key=vertex_type)
        if 'config' not in self.context['visited_vertexes'][uuid]['control']:
            self.context['visited_vertexes'][uuid]['control']['config'] = {}
        config = self.context['visited_vertexes'][uuid]['control']['config']
        Utils.merge_dict(config, iobjs)

    def _store_analytics_uves(self, vertex_type, uuid, fq_name, obj):
        # supported uve types, this check will be removed and
        # it would automatic check in the analytics calss
        supported_list = ['virtual-machine-interface', 'virtual-machine', 'virtual-network']
        if vertex_type not in supported_list:
            return
        aobj = self.analytics.get_object(object_type=vertex_type, object_name=fq_name)
        if aobj:
            self.context['visited_vertexes'][uuid]['analytics']['uve'].update(aobj)


    def _store_agent_config(self, vertex_type, obj):
        url_str = 'Snh_ShowIFMapAgentReq?table_name=&node_sub_string='
        url_str += '%s' % (':'.join(obj[vertex_type]['fq_name']))
        iobjs = self.vrouter.introspect(url_str, key=vertex_type)
        uuid = obj[vertex_type]['uuid']
        if 'config' not in self.context['visited_vertexes'][uuid]['agent']:
            self.context['visited_vertexes'][uuid]['agent']['config'] = {}
        config = self.context['visited_vertexes'][uuid]['agent']['config']
        Utils.merge_dict(config, iobjs)

    # Config detail from agent
    def _get_agent_config_db(self, host_ip, agent_port, vertex_type, vertex):
        config = {}
        url_str = 'http://%s:%s/' % (host_ip, agent_port)
        url_str += 'Snh_ShowIFMapAgentReq?table_name=&node_sub_string='
        url_str += '%s' % (':'.join(vertex[vertex_type]['fq_name']))
        url_dict_resp = Introspect(url=url_str).get()
        config[vertex_type] = url_dict_resp
        return config

    # Config detail from controller
    def _get_control_config_db(self, host_ip, control_port, vertex_type, vertex):
        config = {}
        url_str = 'http://%s:%s/' % (host_ip, control_port)
        url_str += 'Snh_IFMapTableShowReq?table_name=&search_string='
        url_str += '%s' % (vertex[vertex_type]['uuid'])
        url_dict_resp = Introspect(url=url_str).get()
        config[vertex_type] = url_dict_resp
        return config

    def agent_oper_db(self, agent_oper_func, vertex_type, vertex):
        ret = {}
        for vrouter in self.vrouter.vrouter_nodes:
            ret[vrouter['hostname']] = agent_oper_func(vrouter['ip_address'], vrouter['sandesh_http_port'],
                                                      vertex_type, vertex)
        return ret

    def _add_agent_to_context(self, uuid, agent):
        self.context['visited_vertexes'][uuid]['agent'].update(agent)

    def _add_control_to_context(self, uuid, control):
        self.context['visited_vertexes'][uuid]['control'].update(control)

    def _add_config_to_context(self, uuid, config):
        self.context['visited_vertexes'][uuid]['config'].update(config)

if __name__ == '__main__':
    pass
