import logging
import pdb
from pprint import pprint
from logger import logger
from contrail_api import ContrailApi
from introspect import Introspect
from contrail_utils import ContrailUtils
from utils import Utils
from collections import OrderedDict
from vertex_print import vertexPrint
from contrailnode_api import ControlNode
from contrailnode_api import ConfigNode
from contrailnode_api import Vrouter
from contrailnode_api import AnalyticsNode

def create_global_context():
    gcontext = {}
    gcontext['path'] = []
    gcontext['visited_vertexes'] = {}
    gcontext['vertexes'] = {}
    #gcontext['visited_nodes'] = OrderedDict()
    gcontext['visited_nodes'] = {}
    gcontext['visited_vertexes_inorder'] = []
    gcontext['config_api'] = None
    gcontext['config_ip'] = '127.0.0.1'
    gcontext['config_port'] = '8082'
    gcontext['contrail'] = {}
    return gcontext


class baseVertex(object):
    dependant_vertexes = []
    def __init__(self, context=None, vertex_type=None, **kwargs):
        super(baseVertex, self).__init__()
        self.config = None
        self.control = None
        self.analytics = None
        self.vrouter = None
        self.config_objs = {}
        if not context:
            self.context = create_global_context()
        else:
            self.context = context
        self.element = kwargs.get('element', None)
        self.uuid = kwargs.get('uuid', None)
        self.fq_name = kwargs.get('fq_name', None)
        self._set_context_vertex_type(vertex_type)
        self.config_ip = kwargs.get('config_ip', self.context.get('config_ip'))
        self.config_port = kwargs.get('config_port', self.context.get('config_port'))
        self.logger = None
        self._set_contrail_control_objs(self.context)

    def _set_contrail_control_objs(self, context):
        self.config = context['contrail'].get('config', None)
        self.control = context['contrail'].get('control', None)
        self.analytics = context['contrail'].get('analytics', None)
        if not self.config:
            contrail_control = ContrailUtils.get_control_nodes(self.config_ip, self.config_port)
            self.context['contrail']['config'] = self.config = ConfigNode(contrail_control['config_nodes'])
            self.context['contrail']['control'] = self.control = ControlNode(contrail_control['control_nodes'])
            self.context['contrail']['analytics'] = self.analytics = AnalyticsNode(contrail_control['analytics_nodes'])
            self.context['config_ip'] = self.config_ip
            self.context['config_port'] = self.config_port

    def _set_contrail_vrouter_objs(self, vertex_type, obj):
        contrail_info = ContrailUtils.get_contrail_info(obj[vertex_type]['uuid'],
                                                        vertex_type, 
                                                        self.config_ip,
                                                        self.config_port,
                                                        context_path=self.context['path'],
                                                        fq_name=obj[vertex_type]['fq_name'])
        self.vrouter = Vrouter(contrail_info['vrouter'])
                                
    def _set_context_vertex_type(self, vertex_type):
        if vertex_type not in self.context['vertexes']:
            self.context['vertexes'][vertex_type] = []

    def get_context(self):
        return self.context

    def get_context_path(self):
        return self.context['path']

    def get_class_name(self):
        return self.__class__.__name__

    def process_vertexes(self, vertex_type, objs, dependant_vertexes):
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
            self._process_self(vertex_type, uuid, obj)
            self._process_dependants(vertex_type, uuid, fq_name, dependant_vertexes)

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
        #vertex['config'].append(config_obj)
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
                
    def _locate_obj(self, schema_dict, element, **kwargs):
        input_dict = {'match_dict': {}}
        if element != None:
            element_type = element['type']
            element_uuid = element['uuid']
            input_dict = {"type": element_type, 
                          "match_dict" : {'uuid': element_uuid} }
        else:
            input_dict['type'] = kwargs.pop('obj_type')
            for key,value in kwargs.iteritems():
                #if key == 'obj_type':
                #    input_dict['type'] = value
                #else:
                    if value:
                        input_dict['match_dict'][key] = value
                        #for now just one match
                        break
        object_type = input_dict['type']
        key , value = input_dict['match_dict'].popitem()
        try:
            schema_to_use = schema_dict[object_type][key]
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


