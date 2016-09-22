import sys
from vertex_print import vertexPrint
from baseflowvertex import baseFlowVertex
from parser import ArgumentParser
from basevertex import baseVertex
from debugip import debugVertexIP
from debugfip import debugVertexFIP

class debugVertexFlow(baseVertex):
    vertex_type = 'flow'
    non_config_obj = True
    dependant_vertexes = []
    def __init__(self, context=None, source_ip='', dest_ip='',
                 source_vn='', dest_vn='', protocol='',
                 source_port='', dest_port='', **kwargs):
        self.source_ip = source_ip
        self.dest_ip = dest_ip
        self.source_vn = source_vn
        self.dest_vn = dest_vn
        self.protocol = protocol
        self.source_port = source_port
        self.dest_port = dest_port
        self.source_nip = kwargs.get('source_nip', '')
        self.dest_nip = kwargs.get('dest_nip', '')
        self.source_vrf = kwargs.get('source_vrf', '')
        self.dest_vrf = kwargs.get('dest_vrf', '')
        self.source_nvrf = kwargs.get('source_nvrf', '')
        self.dest_nvrf = kwargs.get('dest_nvrf', '')
        self.match_kv = {'source_ip': source_ip, 'dest_ip': dest_ip}
        super(debugVertexFlow, self).__init__(context=context, **kwargs)

    def get_schema(self):
        pass

    def get_uuid(self):
        return ':'.join(['flow', self.source_ip, self.source_nip,
                         self.dest_ip, self.dest_nip,
                         self.source_vrf, self.source_nvrf,
                         self.dest_vrf, self.dest_nvrf,
                         self.source_port, self.dest_port,
                         self.protocol])

    def locate_obj(self):
        self.srcip_vertex = debugVertexIP(instance_ip_address=self.source_ip,
                                          virtual_network=self.source_vn,
                                          context=self.context)
        vertex = self.srcip_vertex.vertexes[0]
        self.srcip_vrouters = self.srcip_vertex.get_vrouters(vertex)
        self.destip_vertex = debugVertexIP(instance_ip_address=self.dest_ip,
                                           virtual_network=self.dest_vn,
                                           context=self.context)
        vertex = self.destip_vertex.vertexes[0]
        self.destip_vrouters = self.destip_vertex.get_vrouters(vertex)
        objs = list()
        objs.append({self.vertex_type: {'uuid': self.get_uuid()}})
        return objs

    def store_config(self, vertex):
        pass

    def get_vrouter_info(self, vertex):
        pass

    def process_self(self, vertex):
        svrouter_flow_vertex = baseFlowVertex(context=self.context,
                                              source_ip=self.source_ip,
                                              vrouters=self.srcip_vrouters,
                                              dest_ip=self.dest_ip, 
                                              **{'source_vrf':self.source_vrf, 'dest_vrf':self.dest_vrf,
                                                 'source_nvrf':self.source_nvrf, 'dest_nvrf':self.dest_nvrf,
                                                 'source_nip':self.source_nip, 'dest_nip':self.dest_nip})
        dvrouter_flow_vertex = baseFlowVertex(context=self.context,
                                              source_ip=self.source_ip,
                                              vrouters=self.destip_vrouters,
                                              dest_ip=self.dest_ip, 
                                              **{'source_vrf':self.source_vrf, 'dest_vrf':self.dest_vrf,
                                                 'source_nvrf':self.source_nvrf, 'dest_nvrf':self.dest_nvrf,
                                                 'source_nip':self.source_nip, 'dest_nip':self.dest_nip})

    '''
    def print_vertex(self):
        vP = vertexPrint([vFlow.fwdflow, vFlow.revflow])
        vP.convert_json()
    '''

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Flow', add_help=True)
    parser.add_argument('--source_ip', help='Source IP of the flow', required=True)
    parser.add_argument('--dest_ip', help='Destination IP of the flow', required=True)
    parser.add_argument('--source_vn', help='VN of the source IP', default='')
    parser.add_argument('--source_vrf', help='VRF of the source IP', default='')
    parser.add_argument('--dest_vn', help='VN of the destination IP', default='')
    parser.add_argument('--dest_vrf', help='VRF of the destination IP', default='')
    parser.add_argument('--protocol', help='L3 Protocol of the flow', default='')
    parser.add_argument('--source_port', help='Source Port of the flow', default='')
    parser.add_argument('--dest_port', help='Destination Port of the flow', default='')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFlow = debugVertexFlow(**args)
    vertexPrint(vFlow).convert_json()
   #context = vIIP.get_context()
    #vertexPrint(context, detail=args.detail)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
