import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
import debugvmi
import debugri

class debugVertexVN(baseVertex):
    vertex_type = 'virtual-network'

    def __init__(self, **kwargs):
        dependant_vertexes = [debugvmi.debugVertexVMI, debugri.debugVertexRI]
        super(debugVertexVN, self).__init__(**kwargs)

    def process_self(self, vertex):
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex)
        self._add_agent_to_context(vertex, agent)
        control = {}
        control['oper'] = {}
        self._add_control_to_context(vertex, control)

    def _get_agent_oper_db(self, introspect, vertex):
        error = False
        vn_uuid = vertex['uuid']
        oper = {}
        vn_info = introspect.get_vn_details(vn_uuid)
        if len(vn_info['vn_list'] or []) == 1:
            vn_rec = vn_info['vn_list'][0]
            oper[vertex['vertex_type']] = vn_rec
        else:
            error = True
            pstr = "Got more vn records, supposed to have one for uuid %s" % (vn_uuid)
            self.logger.error(pstr)
            print pstr
        pstr = "Agent Verified virtual network %s %s" % (vn_uuid, 'with errors' if error else '')
        self.logger.debug(pstr)
        print pstr
        return oper

    def get_schema(self, **kwargs):
        #VN Name, VN UUID, VMI UUID
        schema_dict = {
                "virtual-machine": {
                    "uuid": 'virtual_machine_interface_back_refs.virtual_network_refs'
                },
                "virtual-machine-interface": {
                    "uuid": 'virtual_network_refs'
                }
        }
        return schema_dict

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for VN', add_help=True)
    parser.add_argument('--display_name', help='Display name')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vVN= debugVertexVN(**args)
    #context = vVN.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vVN)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json()
