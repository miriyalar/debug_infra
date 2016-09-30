from pprint import pprint
import json
from utils import Utils
from collections import OrderedDict

class vertexPrint(object):
    def __init__(self, vertex, **kwargs):
        detail = kwargs.get('verbose', False)
        self.vertex = vertex
        self.context = vertex.get_context()

    def get_sorted_vv_summary(self, vertices):
        vertex_type = self.context.get_debugged_vertex()
        insert_at = 0
        for i in range(len(vertices)):
            if vertices[i]['vertex_type'] == vertex_type:
                if i == 0:
                    insert_at = 1
                    continue
                val = vertices.pop(i)
                vertices.insert(insert_at, val)
                insert_at = insert_at + 1
        return vertices

    def get_sorted_vv(self, vertices):
        new_dict = OrderedDict()
        vertex_type = self.context.get_debugged_vertex()
        val = vertices.pop(vertex_type)
        new_dict.update({vertex_type: val})
        new_dict.update(vertices)
        return new_dict

    def _get_objects_from_context(self, object_type=None):
        objs = OrderedDict()
        visited_vertices = OrderedDict()
        if type(self.vertex) is not list:
            self.vertex = [self.vertex]
        vv_in_order = self.context.get_visited_vertices()
        for vertex_dict in vv_in_order:
            vertex_obj = self.context.get_vertex_of_uuid(vertex_dict['uuid'])
            vertex_dict['depth'] = vertex_obj['depth']
            Utils.merge_dict(visited_vertices, {vertex_obj['vertex_type']: [vertex_obj]})
#            vertex_dict['refs'] = vertex_obj['refs']
        objs['summary_of_visited_vertexes'] = self.get_sorted_vv_summary(vv_in_order)
        objs['alarm_status'] = self.context.get_cluster_alarm_status()
        objs['host_status'] = self.context.get_cluster_host_status()
        objs['visited_vertexes'] = self.get_sorted_vv(visited_vertices)
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
        Utils.dict_to_filesystem({'visited_vertexes':convert_dict['visited_vertexes']},
                                 cur_path=cur_path,
                                 console=console_print, depth=3)
        Utils.dict_to_filesystem({'summary_of_visited_vertexes': convert_dict['summary_of_visited_vertexes']},
                                 cur_path=cur_path, console=console_print, depth=1)

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
