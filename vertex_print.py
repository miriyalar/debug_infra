from pprint import pprint
import json
from utils import Utils
from collections import OrderedDict

class vertexPrint(object):
    context = None
    def __init__(self, vertex, **kwargs):
        detail = kwargs.get('verbose', False)
        self.vertex = vertex
        #self._visited_vertexes(context, detail=True)
        #self._visited_vertexes_brief(context)
        #self._context_path(context)

    def _visited_vertexes(self, context, detail=False):
        print 'Visited vertexs:'
        for k,v in context['visited_nodes'].iteritems():
            pprint(k + ':')
            pprint(v, indent=4)

    def _visited_vertexes_brief(self, context = None):
        if context == None:
            context = self.context
        print 'Visited vertexes brief:'
        for vertex in context['visited_vertexes_brief']:
            pprint(vertex['vertex_type'] + ',' + vertex['fq_name'])
            pprint(vertex, indent=4)

    def _context_path(self, context):
        print 'Visited path:'
        pprint(context['path'])

    def _print_config_brief(self, obj, select_list = []):
        #brief_fields_list = ['fq_name', 'href', 'display_name'] + select_list
        brief_fields_list = ['fq_name', 'uuid', 'display_name'] + select_list
        config_objs = obj.get('config', {})
        for hostname, config_obj in config_objs.iteritems():
            obj_type = config_obj.keys()[0]
            obj = config_obj[obj_type]
            print('    {}'.format(obj_type))
            #pprint('vertex_type= ' + obj_type, indent = 8)
            for brief_field in brief_fields_list:
                if brief_field not in obj:
                    print 'Attribute not found in object\n'
                if brief_field == 'fq_name':
                    filed_value = ':'.join(obj[brief_field])
                else:
                    filed_value = obj[brief_field]
                print('      {}'.format('%s : %s'%(brief_field, filed_value)))


    def print_visited_nodes(self, context, select_list = [], detail = False):
        print 'print_visited_nodes'
        visited_vertexes = context.get('visited_vertexes', [])
        for k,v in visited_vertexes.iteritems():
            #print the UUID
            print('  {}'.format(k))
            #pprint(k, indent=4)
            #if detail is not mentioned
            if not detail:
                self._print_config_brief(v, select_list)
            else:
                pprint(v, indent = 2)
            #Print the service specific data
            #pprint(v[agent])
 

    def print_visited_vertexes_inorder(self, context):
        print 'print_visited_vertexes_inorder'
        visited_vertexes = context.get('visited_vertexes_inorder', [])
        for vertex in visited_vertexes:
            filed_print_order = ['vertex_type', 'fq_name', 'uuid', 'display_name']
            for f in filed_print_order:
                if f == 'vertex_type':
                    print('  {}'.format('%s'%(vertex[f])))
                else:
                    print('      {}'.format('%s : %s'%(f, vertex[f])))
 
    def print_object_based_on_uuid(self, uuid, context, detail = False):
        print 'print_object_based_on_uuid'
        visited_vertexes = context.get('visited_vertexes', [])
        if not uuid in visited_vertexes:
            print 'Object not found'
        else:
            if not detail:
                self._print_config_brief(visited_vertexes[uuid], [] )
            else:
                pprint(visited_vertexes[uuid], indent = 2)
                

    def print_object_catalogue(self, detail):
        print 'print_object_catalogue'
        vertexes = self._get_merged_vertex(self.vertex)
        for k,v in vertexes.iteritems():
            #print('  {}'.format(k))
            for item in v:
                if not detail:
                    self._print_config_brief(item)
                else:
                    pprint(item, indent = 2)

    @staticmethod
    def _merge_list_of_dicts(list1, list2):
        list1.extend([x for x in list2 if x not in list1])

    
    def _get_objects_from_context(self, object_type=None):
        objs = OrderedDict()
        visited_vertices = OrderedDict()
        vv_in_order = list()
        if type(self.vertex) is not list:
            self.vertex = [self.vertex]
        for vertex in self.vertex:
            context = vertex.get_context()
            self._merge_list_of_dicts(vv_in_order, context['visited_vertexes_inorder'])
            Utils.merge_dict(visited_vertices, self._get_merged_vertex(vertex))
        objs['summary_of_visited_vertexes'] = vv_in_order
        objs['cluster_status'] = vertex.get_cluster_status()
        objs['alarm_status'] = vertex.get_cluster_alarm_status()
        objs['host_status'] = vertex.get_cluster_host_status()
        objs['visited_vertexes'] = visited_vertices
        return objs

    def convert_json(self, object_type=None, detail=True, file_name='debug_vertexes_output.json'):
        print_list = self._get_objects_from_context(object_type)
        print_list = Utils.remove_none(print_list)
        print_list = Utils.remove_none(print_list)
        with open(file_name, 'w') as fp:
            json.dump(print_list, fp)
            fp.close()

    def convert_to_file_structure(self, object_type=None, cur_path='./', console_print=False):
        convert_dict = self._get_objects_from_context(object_type)
        Utils.dict_to_filesystem({'visited_vertexes':convert_dict['visited_vertexes']}, cur_path=cur_path, console=console_print, depth=3)
        Utils.dict_to_filesystem({'summary_of_visited_vertexes':convert_dict['summary_of_visited_vertexes']}, cur_path=cur_path, console=console_print, depth=1)

    def _get_merged_vertex(self, vertex):
        vertex_dict = OrderedDict()
        obj = vertex.get_vertex()
        if not obj:
            return None
        vertex_dict.update({obj[0]['vertex_type']: obj})
        for vertex in vertex.get_dependent_vertices() or []:
            Utils.merge_dict(vertex_dict, self._get_merged_vertex(vertex))
        return vertex_dict

if __name__ == "__main__":
    import pdb;pdb.set_trace()
    print 'in Main'
    vP = vertexPrint(test_context)   
    vP._visited_vertexes_brief(test_context) 
    vP.print_visited_nodes(test_context, [],False)
    vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',test_context, False)
    vP.print_object_catalogue(test_context, False)
