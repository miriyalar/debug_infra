import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser

class debugVertexSI(baseVertex):
    vertex_type = 'service-instance'
    dependant_vertexes = ['debugVertexVM', 'debugVertexVMI']

    def process_self(self, vertex):
        pass

    def _get_agent_oper_db(self, introspect, vertex):
        pass

    def get_schema(self):
        schema_dict = {
                "service-chain": {
                        "sc_name": self.get_si_from_sc,
                        "vn_name": self.get_si_from_vn,
                },
        }
        return schema_dict

    def get_si_from_sc(self, sc_name):
        objs = list()
        introspect = self.schema.get_inspect_h()
        service_chains = introspect.get_service_chains(sc_name)
        if not service_chains:
            raise Exception('Service chain not found')
        service_instances = service_chains[0]['service_list']
        for service_instance in service_instances:
             objs.append({'fq_name': service_instance})
        return objs

    def get_si_from_vn(self, vn_name):
        return [{'fq_name': 'default-domain:usecase1:si-uc1',
                 'object-type': 'service-instance'},
               ]

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for SI', add_help=True)
    parser.add_argument('--display_name', help='Display name')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vSI= debugVertexSI(**args)
    #context = vSI.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vSI)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_catalogue(context, False)
    #vP.convert_to_file_structure(context)
    vP.convert_json()
