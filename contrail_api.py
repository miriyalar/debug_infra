#!/bin/python
import pdb
import pprint
import json
import re
import logger
from urlparse import urlparse
from contrail_api_con import ContrailApiConnection
from contrail_api_con_exception import ContrailApiConnectionException
from contrail_con_enum import ContrailConError
import datetime

class ContrailApi:
    _ref_to_obj = {
        "virtual_machine_refs" : "virtual-machine",
        "virtual_machine_interface_refs": "virtual-machine-interface"
    }

    def __init__(self, ip = "127.0.0.1", port = "8082", token=None):
        self.log = logger.getLogger(logger_name=self.__class__.__name__)
        self._ip = ip
        self._port = port
        token_header = {'X-AUTH-TOKEN': token} if token else {}
        self._api_con = ContrailApiConnection(ip=ip, port=port,
                        headers = token_header)

    def get_ip(self):
        return self._ip

    def get_port(self):
        return self._port

    def post(self, object_name, data):
        val = self._api_con.post_json(object_name, data)
        return val

    def get_object(self, object_name, url = ''):
        if url:
            o_url = urlparse(url)
            object_path = o_url.path.strip('/')
        elif object_name:
            object_path = object_name
        obj = self._api_con.get(object_path)
        return obj

    def de_ref_obj(self, refs = None, href = None):
        if refs == None and href == None:
            return None
        if refs != None:
            object_path = self.get_object_path(refs['href'])
        elif href != None:
            object_path = self.get_object_path(href)
        obj = self.get_object(object_path)
        return obj

    def get_object_path(self, url):
        o_url = urlparse(url)
        if (o_url == None):
            return None 
        object_path = o_url.path.strip('/')
        return object_path


    def is_ref(self, select):
        if '_refs' in select:
            return True
        elif 'parent_href' in select:
            return True
        elif type(select) == dict:
            if 'to' in select and \
                'href' in select and \
                'uuid' in select :
                return True
            elif 'fq_name' in select and \
                'href' in select and \
                'uuid' in select :
                return True

        else:
            return False

    def verify_obj(self, obj, verify_list, ret_list):
        obj_dict = {}
        obj_dict['type'] = obj.keys()[0]
        obj_dict['uuid'] = obj[obj.keys()[0]]['uuid']
        obj_dict['fq_name'] = ":".join(obj[obj.keys()[0]] ['fq_name'])
        tmp_dicts = obj[obj.keys()[0]]
        obj_dict['neighbors'] = self.get_neighbors(obj, verify_list)
        ret_list.append(obj_dict)

    def get_neighbors(self, object_elem, verify_list = []):
        ref_list = ['refs', 'back_refs']
        parent_href = ['parent_href']
        special_objs = ['routing_instance_refs']
        neighbor_lst = []
        
        full_object_dict = object_elem[object_elem.keys()[0]]
        object_dict = {}
        for verify_element in verify_list:
            object_dict[verify_element] = full_object_dict[verify_element]

        if len(verify_list) <= 0:
            object_dict = full_object_dict

        ref_lst = []
        for key,value in object_dict.iteritems():
            if '_back_refs' in key:
                for i in value:
                    neighbor_str = key.replace('_back_refs', '').replace('_','-') + ":" + ":".join(i['to'])
                    ref_lst.append(neighbor_str)
            elif '_refs' in key:
                #Would it be a list here
                for i in value:
                    if 'attr' in i and i['attr'] != None:
                        neighbor_str = object_elem.keys()[0] + "-" +  key.replace('_refs', '').replace('_', '-') + ":attr(" +":".join(object_dict['fq_name'])  + "," +  ":".join(i['to']) + ")"
                        ref_lst.append(neighbor_str)
                    else:
                        neighbor_str = key.replace('_refs', '').replace('_', '-') + ":" + ":".join(i['to'])
                        ref_lst.append(neighbor_str)
            elif 'parent_href' in key:
                fq_name_len = len(object_dict['fq_name'])
                ref_lst.append(object_dict['parent_type'] + ":" + \
                            ":".join(object_dict['fq_name'][:fq_name_len-1]))
            elif type(value) == list:
                for i in value:
                    if 'to' in i and \
                        'href' in i and \
                        'uuid' in i:
                        neighbor_str = re.match(r"(.*)s", key).group(1).replace('_', '-') + ":" + ":".join(i['to']) 
                        ref_lst.append(neighbor_str)

        return ref_lst


    def translate_config_obj(self, cfg_lst):
        translation_list = []
        for item in cfg_lst:
            obj_lst = item
            for obj in obj_lst:
                obj_dict = {}
                obj_dict['type'] = obj.keys()[0]
                obj_dict['uuid'] = obj[obj.keys()[0]]['uuid']
                obj_dict['fq_name'] = ":".join(obj[obj.keys()[0]] ['fq_name'])
                tmp_dicts = obj[obj.keys()[0]]
                obj_dict['neighbors'] = self.get_neighbors(obj)
                translation_list.append(obj_dict)
        return translation_list 

    def get_object_deep_multiple_select(self, object_name,
                                        object_path_list = [],
                                        where = ''):
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


        ret_list = []
        for object_path in object_path_list:
            select_list = self.get_object_deep(object_name, 
                                    object_path,
                                    object_dict = None,
                                    where = where,
                                    detail = True,
                                    de_ref = True, strip_obj_name = False)

            ret_list.append(select_list)
        return ret_list


    def _get_obj_matching_with_fields(self, obj, field, depth=0):
        field_list = field.split('.')
        if obj != None and depth != len(field_list):
            ret_list = []
            d_field = field_list[depth]
            cur_field = d_field.split('==')[0]
            if cur_field in obj:
                new_obj = obj[cur_field]
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
                    #return [new_obj]
            else:
                return ret_list
        elif obj != None and depth == len(field_list):
            return [obj]


    def _is_obj_matching_with_filters(self, obj, filters):
        filters_list = filters.split('&')
        filtered_objs = {}
        for filter in filters_list:
            filter_key = filter.split('=')[0]
            filter_value = filter.split('=')[1]
            filtered_objs[filter_key] = self._get_obj_matching_with_fields(obj.values()[0], filter_key, depth=0)
            match = False
            for filtered_obj in filtered_objs[filter_key]:
                if filter_value == filtered_obj:
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
        _quick_list = ['uuid']
        ret_list = []
        ret_dict = {}
        object_names =  object_name + "s"
        url = ("%s?detail=True") % (object_names)

	#Cut there a get object quick
        filters_list = filters.split(',')
        for filter_obj in filters_list:
            filter_tmp = filter_obj.split('=')
            if filter_tmp[0] in _quick_list:
                new_url = '%s/%s' % (object_name, filter_tmp[1])		
		obj = self._api_con.get(new_url)
		ret_dict[object_names] = [obj]
		return ret_dict


        objs = self._api_con.get(url)
        if not object_names in objs and \
            len(objs[object_name]) <= 0:
            print "No objects Found"
            return ret_list
        else :
            obj_list = objs[object_names]

        for obj in obj_list:
            if self.is_ref(obj):
                deref_obj = self.de_ref_obj(obj)
                if(len(filters) >= 0 and self._is_obj_matching_with_filters(deref_obj, filters)):
                    ret_list.append(deref_obj)
                elif (len(filters) <= 0):
                    ret_list.append(deref_obj)
            else:
                if(self._is_obj_matching_with_filters(obj, filters)):
                    ret_list.append(obj)
        ret_dict[object_names] = ret_list
        return ret_dict
        
        


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
        if object_path_list_str != None and object_path_list_str != '':
            object_path_list = object_path_list_str.split('.')
        else:
            object_path_list = []
        object_path_list.insert(0, object_name) 
        if depth == 0 and object_dict == None:

            object_name = object_path_list[depth]
            objs = self.get_object_with_filters(object_name, where)
            object_names =  object_name + "s"
            if not object_names in objs and \
                len(objs[object_name]) <= 0:
                print "No objects Found"
                return []
            else :
                obj_list = objs[object_names]

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
            obj = object_dict[object_dict.keys()[0]]
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
                            #if ret_objs == None:
                            #    import pdb; pdb.set_trace()
                            ret_list = ret_list + ret_objs
                    return ret_list
                else:
                    #if new_obj == None:
                    #   pdb.set_trace()	
                    return [new_obj]
            else:
                pstr = 'Error: path %s not found, in %s, %s' % \
                       (cur_object, obj['display_name'], ':'.join(obj['fq_name']))
                print pstr
                return []

        elif object_dict != None and depth == len(object_path_list):
            return [object_dict]

    def get_object_multiple_select(self, object_name, where = '', select_list = '', detail = False, de_ref = False, strip_obj_name = False):
        """
        Return a list of objects mentioned in the select_list,
        Which are attributes of the object given in the object_name,
        matching the where field.

        Keyword arguments:
        object_name -- object from which the walk would begin.
        select_list -- A list of objects which are directly accessible from the object given in object_name .             
        where -- A match criteria based upon which the object of type object_name will be selected.

        return:
        A list of objects          
        """

        obj = self.get_object_with_filters(object_name, where)
        object_names =  object_name + "s"
        if not object_names in obj and \
            len(obj[object_name]) <= 0:
            print "No objects Found"
            return []
        elif len(select_list) <= 0:
            obj_list = obj[object_names]
            return [obj_list]
        else :
            obj_list = obj[object_names]
            ret_obj_list = []
            for item in obj_list:
                select_items = select_list.split(',')
                if not object_name in item:
                    print "object name not in items"
                    return []
                for select in select_items:
                    select_list = []                    
                    if object_name in item and select in item[object_name]:
                        item_elem = item[object_name][select]
                        
                        if de_ref and self.is_ref(select):
                            if type(item_elem) == list:
                                for i in item_elem:
                                    if (strip_obj_name):
                                        select_list.append(self.de_ref_obj(refs = i).get(self._ref_to_obj[select]))
                                    else:
                                        select_list.append(self.de_ref_obj(refs = i))
                            else:
                                select_list.append(self.de_ref_obj(href = item_elem))
                        else:
                            select_list.append(item[object_name][select])
                    ret_obj_list.append(select_list)
            return ret_obj_list



 
#end of ContrailApi


if __name__ == "__main__":
    pdb.set_trace()
    #first test to try out what needs to be done
#    test_first_floating_ip('7.7.7.3')
#    optimize_floating_ip_de_ref(given_ip= '7.7.7.3')
    #debug_floating_ip('7.7.7.3')
    debug_new_floating_ip('7.7.7.3')

