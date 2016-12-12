#
# Copyright (c) 2016 Juniper Networks, Inc. All rights reserved.
#
import pdb
import logger
import pprint
import json
import re
from urlparse import urlparse
from contrail_api_con import ContrailApiConnection

class ContrailUVE:
    """
    Analytics node connection to fetch UVE objects
    """
    def __init__(self, ip = "127.0.0.1", port = "8081", token=None):
        self.log = logger.getLogger(logger_name=self.__class__.__name__)
        token_header = {'X-AUTH-TOKEN': token} if token else {}
        self._api_con = ContrailApiConnection(ip=ip, port=port,
                                              headers=token_header)


    def is_ref(self, select):
        if 'href' in select:
            return True
        else:
            return False


    def _get_object(self, object_name, url=''):
        if url:
            o_url = urlparse(url)
            object_path = o_url.path.strip('/')
        elif object_name:
            object_path = object_name
        obj = self._api_con.get(object_path)
        return obj


    def get_object_path(self, url):
        o_url = urlparse(url)
        if (o_url == None):
            return None 
        object_path = o_url.path.strip('/') + '?' + o_url.query
        return object_path


    def de_ref_obj(self, refs = None, href = None):
        if refs == None and href == None:
            return None
        if refs != None:
            object_path = self.get_object_path(refs['href'])
        elif href != None:
            object_path = self.get_object_path(href)
        obj = self._get_object(object_path)
        return obj


    def _get_obj_matching_with_fields(self, obj, field, depth=0):
        ret_list = []
        if obj is None:
            return ret_list
        field_list = field.split('.')
        d_field = field_list[depth]
        cur_field = d_field.split('==')[0]
        if cur_field in obj:
            new_obj = obj[cur_field]
            if depth == len(field_list) - 1:
                return [new_obj]
            if type(new_obj) == list:
                for element in new_obj:
                    ret_objs = self._get_obj_matching_with_fields(element, 
                                                                  field, 
                                                                  depth=depth+1)
                    ret_list = ret_list + ret_objs
                return ret_list
            else:
                ret_objs = self._get_obj_matching_with_fields(new_obj,
                                                              field,
                                                              depth=depth+1)
                ret_list = ret_list + ret_objs
                return ret_list
        else:
            return ret_list

    def _is_obj_matching_with_filters(self, obj, filters):
        if filters:
            filters_list = filters.split('&')
        else:
            filters_list = []
        filtered_objs = {}
        for filter in filters_list:
            filter_key = filter.split('=')[0]
            filter_value = filter.split('=')[1]
            filtered_objs[filter_key] = self._get_obj_matching_with_fields(obj.values()[0], filter_key, depth=0)
            match = False
            for filtered_obj in filtered_objs[filter_key]:
                if filter_value == str(filtered_obj):
                    match = True
            if not match:
                return False
        return True

    def get_object_with_filters(self, object_name, filters):
        """
        Return a list of objects mentioned in the object_name,
        based on the filter specified,
        This method can be obsoleted if API server is supporting all filters.

        Keyword arguments:
        object_name -- object for which the filter should be applied.
        filters -- A list of filters to be applied on the object.
        TODO:supporting only one filter for now 

        return:
        A list of objects          
        """
        ret_list = []
        ret_dict = {}
        object_names = object_name + "s"
        url = ("%s") % (object_names)
        if filters:
            filters_list = filters.split(',')
        else:
            filters_list = []
        for filter_obj in list(filters_list):
            filter_tmp = filter_obj.split('=')
            if filter_tmp[0] == 'name':
                new_url = '%s/%s?flat' % (object_name, filter_tmp[1])		
		obj = self._api_con.get(new_url)
                ret_list.append(obj)
                return ret_list
                #filters_list.remove(filter_obj)
        objs = self._api_con.get(url)
        for obj in objs:
            if self.is_ref(obj):
                deref_obj = self.de_ref_obj(obj)
                if(len(filters) >= 0 and self._is_obj_matching_with_filters(deref_obj, filters)):
                    ret_list.append(deref_obj)
                elif (len(filters) <= 0):
                    ret_list.append(deref_obj)
            else:
                if(self._is_obj_matching_with_filters(obj, filters)):
                    ret_list.append(obj)
        #ret_dict[object_name] = ret_list
        return ret_list

    def get_object_deep(self, object_name, object_path_list_str = '',
                         object_dict = None, where = '',
                         detail = False, de_ref = False,
                         strip_obj_name = False, depth = 0):
        """
        Return a list of objects mentioned in the objecat_path_list,
        Which are in turn accessible from the object_name,
        matching the where field.

        Keyword arguments:
        object_name -- object from which the walk would begin.
        object_path_list -- A list of path from the object to be walked separated by .             
        where -- A match criteria based upon which the object to be walked is selected upon.

        return:
        A list of objects          
        """
        if isinstance(object_path_list_str, list):
            ret_list = []
            for object_path in object_path_list_str:
                objs = self.get_object_deep(object_name, object_path,
                                            object_dict, where, detail,
                                            de_ref, strip_obj_name, depth)
                ret_list.extend(objs)
            return ret_list

        if object_path_list_str and ',' in object_path_list_str:
            ret_list = []
            object_path_list = object_path_list_str.split(',')
            for object_path in object_path_list:
                if not object_path:
                    continue
                objs = self.get_object_deep(object_name, object_path,
                                            object_dict, where, detail,
                                            de_ref, strip_obj_name, depth)
                ret_list.extend(objs)
            #return [list(item) for item in zip(*ret_list)]
            return ret_list
                
        if object_path_list_str != None and object_path_list_str != '':
            object_path_list = object_path_list_str.split('.')
        else:
            object_path_list = []
        object_path_list.insert(0, object_name) 
        if depth == 0 and object_dict == None:
            object_name = object_path_list[depth]
            obj_list = self.get_object_with_filters(object_name, where)
            #if not object_name in objs:
            #    print "No objects Found"
            #    return []
            #else :
            #    obj_list = objs[object_name]
            ret_list = []
            for obj in obj_list:
                ret_objs = self.get_object_deep(object_name, object_path_list_str, obj,
                                                 where, detail, de_ref,
                                                 strip_obj_name,
                                                 depth = depth + 1)
                ret_list = ret_list + ret_objs
            return ret_list
        elif object_dict != None and depth != len(object_path_list):
            ret_list = []
            cur_object = object_path_list[depth]
            object_dict.pop('ref', None)
            #obj = object_dict[object_dict.keys()[0]]
            obj = object_dict
            if cur_object in obj:
                new_obj = obj[cur_object]
                if type(new_obj) == list:
                    for element in new_obj:
                        if self.is_ref(element):
                            obj = self.de_ref_obj(element)
                            ret_objs = self.get_object_deep(object_name, object_path_list_str, obj,
                                                                     where , detail,
                                                                     de_ref, strip_obj_name,
                                                                         depth = depth + 1)
                            ret_list = ret_list + ret_objs
                    if not ret_list:
                        return [new_obj]
                    return ret_list
                elif self.is_ref(cur_object):
                    obj = self.get_object(object_name, url=new_obj)
                    ret_objs = self.get_object_deep(object_name, object_path_list_str, obj,
                                                    where, detail, de_ref, strip_obj_name,
                                                    depth = depth+1)
                    ret_list = ret_list + ret_objs
                    return ret_list
                else:
                    ret_objs = self.get_object_deep(object_name, object_path_list_str, new_obj,
                                                    where, detail, de_ref, strip_obj_name,
                                                    depth = depth+1)
                    ret_list = ret_list + ret_objs
                    return ret_list
            else:
                #pstr = 'Warning: path %s not found.' % (cur_object)
                #print pstr
                return [None]
        elif object_dict != None and depth == len(object_path_list):
            return [object_dict]


    def get_object(self, object_name, obj_type, select_fields = [], found_error=True):
        objname = "analytics/uves/" + obj_type
        if object_name:
            where = 'name=%s' % (object_name)
        else:
            where = ''
        objpath_list_str = ','.join(select_fields)
        values = self.get_object_deep(objname, objpath_list_str, where=where)
        if not object_name and not select_fields:
            ret_dict = {obj_type: values}
        else:
            keys = select_fields
            ret_dict = {k: v for k, v in zip(keys, values)}
        return ret_dict
        '''
        uve_path = "analytics/uves/" + obj_type
        object_path = uve_path + "/" +  object_name + "?flat"
        obj = self._api_con.get(object_path)
        ret_dict = {}

        if len(select_fields) <= 0:
            return obj

        for element in select_fields:
            element_list = element.split('.')
            tmp_obj = obj
            not_found = False
            for level in element_list:
                if level in tmp_obj:
                    tmp_obj = tmp_obj[level]
                else:
                    if found_error:
                        pstr = 'Error: Object %s, %s not found, trying to get %s' % \
                               (obj_type, object_name, level)
                        print pstr
                    not_found = True
                    break;
            if not_found == False:
                ret_dict[element] = tmp_obj
        if obj.get('ref', None):
            ret_dict['ref'] = obj['ref']
        return ret_dict
        '''

def get_dashboard(analytics_ip = '10.84.17.5', port = 8081):
    from collections import OrderedDict
    dashboard = OrderedDict({
        'vrouter': {'object_type': 'vrouter', 'description': 'Virtual Routers'},
        'config-node': {'object_type': 'config-node', 'description': 'Config Nodes'},
        'control-node': {'object_type': 'control-node', 'description': 'Control Nodes'},
        'database-node': {'object_type': 'database-node', 'description': 'Database Nodes'},
        'analytics-node': {'object_type': 'analytics-node', 'description': 'Analytics Nodes'},
        'virtual-machine-interface': {'object_type': 'virtual-machine-interface', 'description': 'Interfaces'},
        'virtual-machine': {'object_type': 'virtual-machine', 'description': 'Instances'},        
    })
    uve_obj = ContrailUVE(ip = analytics_ip, port = port)
    object_name = ''
    for k, entry in dashboard.iteritems():
        objs = uve_obj.get_object(object_name, entry['object_type'])
        entry['count'] = len(objs[entry['object_type']])
    return dashboard
    
def get_vm_info(uuid = ""):
    uve_obj = ContrailUVE(ip = "10.84.17.5", port = 8081)
    fq_name = 'b9ed1f6f-4846-4492-a151-0bd50e02c7cd'
    vrouter_obj = uve_obj.get_object(fq_name, "virtual-machine", 
                                     select_fields = ['UveVirtualMachineAgent.vrouter'])
    vrouters = uve_obj.get_object('', 'vrouter')
    test_obj = uve_obj.get_object(fq_name, "virtual-machine", 
                                  select_fields = ['UveVirtualMachineAgent.vrouter', 'VirtualMachineStats.cpu_stats'])
    #node_status = uve_obj.get_object_deep('analytics/uves/vrouter', 'NodeStatus.deleted', where='name=a3s19')
    vrouters = uve_obj.get_object_deep('analytics/uves/vrouter')
    print "Virtual Routers: %s" % (len(vrouters))
    configs = uve_obj.get_object_deep('analytics/uves/config-node')
    print "Config Nodes: %s" % (len(configs))
    control = uve_obj.get_object_deep('analytics/uves/control-node')
    print "Control Nodes: %s" % (len(control))
    db = uve_obj.get_object_deep('analytics/uves/database-node')
    print "Database Nodes: %s" % (len(db))
    analytics = uve_obj.get_object_deep('analytics/uves/analytics-node')
    print "Database Nodes: %s" % (len(analytics))
    #vns = uve_obj.get_object_deep('analytics/uves/virtual-network')
    #print "Virtual Networks: %s" % (len(vns))
    int_list = uve_obj.get_object_deep('analytics/uves/vrouter', 'VrouterAgent.interface_list')
    print "Interfaces: %s" %(len(int_list))
    vm_list = uve_obj.get_object_deep('analytics/uves/vrouter', 'VrouterAgent.virtual_machine_list')
    print "Instances: %s" %(len(vm_list))
    #import pdb; pdb.set_trace()
    int_vm_list = uve_obj.get_object('', 'vrouter', select_fields = ['VrouterAgent.interface_list','VrouterAgent.virtual_machine_list'])
    peer_list = uve_obj.get_object('', 'vrouter', select_fields = ['VrouterAgent.xmpp_peer_list', 
                                                                   'VrouterAgent.self_ip_list',
                                                                   'VrouterAgent.sandesh_http_port'])
    #import pdb; pdb.set_trace()

    #vrouter = uve_obj.get_object( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1' ,"virtual-machine", select_fields = ['UveVirtualMachineAgent.vrouter'])
    #xmpp_peer_list =  uve_obj.get_object( 'a3s19' ,"vrouter", select_fields = ['VrouterAgent.xmpp_peer_list'])

if __name__ == "__main__":
    #first test to try out what needs to be done
#    test_first_floating_ip('7.7.7.3')
#    optimize_floating_ip_de_ref(given_ip= '7.7.7.3')
    #debug_floating_ip('7.7.7.3')
    #get_vm_info(uuid = "")
    get_dashboard()
