import pdb
import logger
from introspect import Introspect
from contrail_utils import ContrailUtils
from utils import Utils
from collections import OrderedDict, defaultdict
from contrailnode_api import Vrouter
from abc import ABCMeta, abstractmethod
from context import Context
import logging

def get_logger(name, **kwargs):
    verbose = kwargs.get('verbose', None)
    loglevel = logging.DEBUG if verbose else logging.INFO
    return logger.getLogger(logger_name=name, console_level=loglevel)

def create_vertex(vertex_type, **kwargs):
    vertex = defaultdict(dict)
    vertex.update({
        'vertex_type': vertex_type,
        'config': {},
        'agent' : defaultdict(dict),
        'control': defaultdict(dict),
        'analytics': {'uve':{}},
    })
    for k,v in kwargs.iteritems():
        vertex.update({k: v})
    return vertex

class baseVertex(object):
    '''Abstract Base Class for Vertex'''
    __metaclass__ = ABCMeta
    def __init__(self, context=None, **kwargs):
        self.logger = get_logger(name=self.get_class_name(), **kwargs)
        self.config = None
        self.control = None
        self.analytics = None
        self.vrouter = None
        self.vertexes = []
        self.ref_vertexes = []
        self.config_objs = {}
        self.dependent_vertex_objs = list()
        if not context:
            self.context = Context(**kwargs)
        else:
            self.context = context
        if self._is_vertex_type_exists_in_path():
            return
        self.config_ip = self.context.config_ip
        self.config_port = self.context.config_port
        self.depth = self.context.depth
        self.element = kwargs.get('element', None)
        self.uuid = kwargs.get('uuid', None)
        self.fq_name = kwargs.get('fqname', None)
        if isinstance(self.fq_name, str):
            self.fq_name = self.fq_name.split(':')
        self.display_name = kwargs.get('display_name', None)
        self.obj_type = kwargs.get('obj_type', None) or self.vertex_type
        self.token = self.context.token
        if not self.token:
            self.logger.warn('Authentication failed: Unable to fetch token from keystone')
        self._set_contrail_control_objs()
        
        self.schema = self.get_schema()
        if not self.element:
            if not hasattr(self, 'match_kv') or not any(self.match_kv.itervalues()):
                self.match_kv = {'uuid': self.uuid, 'fq_name': self.fq_name,
                                 'display_name': self.display_name}
            if not any(self.match_kv.itervalues()):
                raise Exception('Nothing to match, please check match args')
        self.process_vertexes(self._locate_obj())

    @abstractmethod
    def process_self(self, vertex):
        pass

    @abstractmethod
    def get_schema(self, context, **kwargs):
        pass

    def _set_contrail_control_objs(self):
        self.config = self.context.config
        self.control = self.context.control
        self.analytics = self.context.analytics
        self.context.get_cluster_status()

    def _set_contrail_vrouter_objs(self, vertex_type, obj):
        contrail_info = ContrailUtils(token=self.token).get_contrail_info(
                                                        obj[vertex_type]['uuid'],
                                                        vertex_type,
                                                        config_ip=self.config_ip,
                                                        config_port=self.config_port,
                                                        context_path=self.context.get_path(),
                                                        fq_name=':'.join(obj[vertex_type]['fq_name']))
        self.vrouter = Vrouter(contrail_info['vrouter'])

    def get_context(self):
        return self.context

    def get_class_name(self):
        return self.__class__.__name__

    def process_vertexes(self, objs):
        vertex_type = self.vertex_type
        for obj in objs:
            uuid = obj[vertex_type]['uuid']
            fq_name = ':'.join(obj[vertex_type]['fq_name'])
            self._set_contrail_vrouter_objs(vertex_type, obj)
            if self.context.is_visited_vertex(uuid):
                self.ref_vertexes.append(self.context.get_vertex_of_uuid(uuid))
                continue
            vertex = self._store_vertex(vertex_type, uuid, obj)
            self._store_config(vertex, uuid, obj, self.config_objs)
            self._store_control_config(vertex, obj)
            self._store_analytics_uves(vertex, obj)
            self._store_agent_config(vertex, obj)
            self.process_self(vertex)
            if self.depth == 0:
                continue
            self.context.depth = self.context.depth - 1
            if getattr(self, 'dependant_vertexes', None):
                self._process_dependants(uuid, fq_name)

    def _add_to_context_path(self, element):
        self.current_frame = element
        self.context.add_path(element)
        self.logger.debug('Add '+ str(self.context.get_path()))

    def _remove_from_context_path(self, element):
        self.context.delete_path(element)
        self.logger.debug('Remove' + str(self.context.get_path()))

    def _process_dependants(self, uuid, fq_name):
        from debugvm import debugVertexVM
        from debugvn import debugVertexVN
        from debugvmi import debugVertexVMI
        from debugsg import debugVertexSG
        from debugip import debugVertexIP
        from debugfip import debugVertexFIP
        element = self._create_element(vertex_type=self.vertex_type,
                                       uuid=uuid,
                                       fq_name=fq_name)
        for dependant_vertex in self.dependant_vertexes:
            self._add_to_context_path(element)
            self.dependent_vertex_objs.append(
                 eval(dependant_vertex)(context=self.context, element=element))
            self._remove_from_context_path(element)

    def get_dependent_vertices(self):
        return self.dependent_vertex_objs

    def get_vertex(self):
        return self.vertexes

    def _store_vertex(self, vertex_type, uuid, config_obj):
        fq_name = ':'.join(config_obj[vertex_type]['fq_name'])
        vertex = create_vertex(vertex_type, uuid=uuid, fq_name=fq_name)
        self.vertexes.append(vertex)
        self.context.add_vertex(vertex)
        return vertex

    def _is_vertex_type_exists_in_path(self):
        for element in self.context.get_path():
            if element['type'] == self.vertex_type:
                return True
        return False

    def _create_element(self, vertex_type, uuid, fq_name):
        element = {}
        element['type'] = vertex_type
        element['uuid'] = uuid
        element['fq_name'] = fq_name
        return element

    def _locate_obj(self):
        input_dict = {'match_dict': {}}
        if self.element != None:
            object_type = self.element['type']
            key = 'uuid'
            where = '%s=%s' % (key, self.element['uuid'])
        else:
            object_type = self.obj_type
            where = ''
            if self.match_kv.get('uuid', None):
                key = 'uuid'
            else:
                self.match_kv.keys()[0]
            for k,v in self.match_kv.iteritems():
                if v:
                    if where:
                        where += '&'
                    where += '%s=%s' % (k, v)
        try:
            schema_to_use = self.schema[object_type][key]
        except KeyError:
            schema_to_use = None
        ret_obj_list, self.config_objs = self.config.get_object(object_type,
                                                                schema_to_use=schema_to_use,
                                                                where=where)
        return ret_obj_list

    def _store_config(self, vertex, uuid, obj, config_objs):
        cobj = config_objs.get(uuid, None)
        if cobj:
            vertex['config'].update(cobj)

    def _store_control_config(self, vertex, obj):
        vertex_type = vertex['vertex_type']
        fq_name_str = ':'.join(obj[vertex_type]['fq_name'])
        iobjs = defaultdict(dict)
        for hostname, inspect in self.context.get_control_inspect_h():
            iobjs[hostname][vertex_type] = inspect.get_config(fq_name_str=fq_name_str)
        config = vertex['control']['config']
        Utils.merge_dict(config, iobjs)

    def _store_analytics_uves(self, vertex, obj):
        # supported uve types, this check will be removed and
        # it would automatic check in the analytics calss
        vertex_type = vertex['vertex_type']
        fq_name = ':'.join(obj[vertex_type]['fq_name'])
        supported_list = ['virtual-machine-interface', 'virtual-machine', 'virtual-network']
        if vertex_type not in supported_list:
            return
        aobj = self.analytics.get_object(object_type=vertex_type, object_name=fq_name)
        if aobj:
            vertex['analytics']['uve'].update(aobj)

    def _store_agent_config(self, vertex, obj):
        vertex_type = vertex['vertex_type']
        fq_name_str = ':'.join(obj[vertex_type]['fq_name'])
        iobjs = defaultdict(dict)
        for hostname, inspect in self.get_vrouters():
             iobjs[hostname][vertex_type] = inspect.get_config(fq_name_str=fq_name_str)
        config = vertex['agent']['config']
        Utils.merge_dict(config, iobjs)

    def agent_oper_db(self, agent_oper_func, vertex):
        ret = {}
        for hostname, inspect in self.get_vrouters():
            ret[hostname] = agent_oper_func(inspect, vertex)
        return ret

    def get_vrouters(self):
        inspect_h = []
        for vrouter in self.vrouter.get_nodes():
            inspect_h.append((vrouter['hostname'], self.vrouter.get_inspect_h(vrouter['ip_address'])))
        return inspect_h

    def _add_agent_to_context(self, vertex, agent):
        vertex['agent'].update(agent)

    def _add_control_to_context(self, vertex, control):
        vertex['control'].update(control)

    def _add_config_to_context(self, vertex, config):
        vertex['config'].update(config)

    def _get_attr(self, attr, vertex, service, subtype, hostname):
        if not vertex:
            return None
        vertex_type = vertex['vertex_type']
        obj = vertex[service]
        if service != 'config':
           obj = obj[subtype] if subtype else obj['config']
        obj = obj[hostname] if hostname else obj.values()[0]
        d = obj[vertex_type] if vertex_type in obj else obj
        for key in attr.split('.'):
            try:
                d = d[key]
            except KeyError:
                break
            except TypeError:
                try:
                    d = d[int(key)]
                except IndexError:
                    break #Should we return None or until we had parsed
        return d

    def get_attr(self, attr, vertex=None, service='config', subtype=None, hostname=None):
        '''
           Fetch value of the requested attribute from the vertex
           Possible services: config, control, agent, analytics
           if service is not config do provide subtype as oper or config(default: config)
           attr can be hierarchy of '.' separated keys
           for eg: virtual_machine_interface_mac_addresses.mac_address.0
        '''
        vertices = [vertex] if vertex else self.vertexes
        ret_list = []
        for vertex in vertices:
            ret_list.append(self._get_attr(attr, vertex, service, subtype, hostname))
        if len(ret_list) == 0:
            for vertex in self.ref_vertexes:
                ret_list.append(self._get_attr(attr, vertex, service, subtype, hostname))
        return ret_list

if __name__ == '__main__':
    pass
