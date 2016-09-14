import sys
from vertex_print import vertexPrint
from baseflowvertex import baseFlowVertex
from parser import ArgumentParser

class debugVertexFlow():
    def __init__(self, context=None, source_ip=None, dest_ip=None,
                 source_vn=None, dest_vn=None, protocol=None,
                 source_port=None, dest_port=None, **kwargs):
        self.source_ip = source_ip
        self.dest_ip = dest_ip
        self.source_vn = source_vn
        self.dest_vn = dest_vn
        self.protocol = protocol
        self.source_port = source_port
        self.dest_port = dest_port
        self.context = context
        self.kwargs = kwargs

    def process(self):
        self.fwdflow = baseFlowVertex(source_ip=self.source_ip,
                                      dest_ip=self.dest_ip,
                                      source_vn=self.source_vn,
                                      dest_vn=self.dest_vn,
                                      protocol=self.protocol,
                                      source_port=self.source_port,
                                      dest_port=self.dest_port,
                                      context = self.context,
                                      **self.kwargs)
        self.context = self.fwdflow.get_context()
        source_vrf = self.fwdflow.source_vrf
        dest_vrf = self.fwdflow.dest_vrf
        self.revflow = baseFlowVertex(source_ip=self.dest_ip,
                                      dest_ip=self.source_ip,
                                      source_vn=self.dest_vn,
                                      dest_vn=self.source_vn,
                                      protocol=self.protocol,
                                      source_port=self.dest_port,
                                      dest_port=self.source_port,
                                      source_vrf=dest_vrf,
                                      dest_vrf=source_vrf,
                                      context=self.context,
                                      **self.kwargs)

    def print_vertex(self):
        vP = vertexPrint([vFlow.fwdflow, vFlow.revflow])
        vP.convert_json()

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Flow', add_help=True)
    parser.add_argument('--source_ip', help='Source IP of the flow', required=True)
    parser.add_argument('--dest_ip', help='Destination IP of the flow', required=True)
    parser.add_argument('--source_vn', help='VN of the source IP')
    parser.add_argument('--dest_vn', help='VN of the destination IP')
    parser.add_argument('--protocol', help='L3 Protocol of the flow')
    parser.add_argument('--source_port', help='Source Port of the flow')
    parser.add_argument('--dest_port', help='Destination Port of the flow')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFlow = debugVertexFlow(**args)
    vFlow.process()
    vFlow.print_vertex()
    #context = vIIP.get_context()
    #vertexPrint(context, detail=args.detail)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
