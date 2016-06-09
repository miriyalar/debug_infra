context = {}
gcontext['path'] = []
gcontext['visited_vertexes'] = {'uuid1': vertex1, 'uuid2': vertex2 ...}
gcontext['detail_visited_vertexes'] = []

vertex = {
    'uuid': uuid
    'fq_name': fq_name,
    'vertex_type': vertex_type,
    'config': [{}],
    'agent' : [{
        'config': config_obj,
        'oper': oper_obj,
        'any other params': its_value
    }]
    'control': [{}],
    'analytics': [{}],
    'any other': its_value
}

gcontext['vertexes'][vertex_type] = [vertex1, vertex2, ...]
#gcontext[vertex_type] = [vertex1, vertex2, ...]




vertex = {
    'uuid': uuid
    'fq_name': fq_name,
    'vertex_type': vertex_type,
    'config': [{}],
    'agent' : [{
        'config': config_obj,
        'oper': oper_obj,
        'any other params': its_value
    }]
    'control': [{}],
    'analytics': [{}],
    'any other': its_value
}

config = {
    'count': count,
    'config_node_<host_name>': {
    }
}

class control_node(object):
    [(ip_address,sandesh_port)]
    introspect(url)
    

locate_obj
- Locate the objects
- Gets the contrail info
- Creates the config, control, agent, analytics objects
- Returns the list of objs

process_vertex
- Pass of list of objs

