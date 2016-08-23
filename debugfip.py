import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser

class debugVertexFIP(baseVertex):
    dependant_vertexes = ['debugVertexVMI']
    vertex_type = 'floating-ip'

    def __init__(self, context=None, **kwargs):
        self.floating_ip_address = kwargs.get('floating_ip_address', None)
        self.match_kv = {'floating_ip_address': self.floating_ip_address}
        super(debugVertexFIP, self).__init__(context=context, **kwargs)

    def get_schema(self):
        schema_dict = {
                "virtual-machine-interface": {
                        'uuid': 'floating_ip_back_refs',
                }
        }
        return schema_dict

    def process_self(self, vertex):
        # Update flaotingip address if doesnt exist
        if not self.floating_ip_address:
            self.floating_ip_address = self.get_attr('floating_ip_address', vertex)
        # Agent
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex)
        self._add_agent_to_context(vertex, agent)
        # Control
        control = {}
        control['oper'] = {}
        self._add_control_to_context(vertex, control)

    def _get_agent_oper_db(self, inspect_h, vertex):
        oper = {}
        vmi_uuid = None
        adjacency_type='virtual-machine-interface'
        adjacency_list = inspect_h.get_adjacencies(uuid=vertex['uuid'],
                                                   adjacency_type=adjacency_type)
        for adjacency in adjacency_list:
            if adjacency[0] == adjacency_type:
                vmi_uuid = adjacency[2]
                break
        if not vmi_uuid:
            self.logger.error("Agent Error, interface is not found in the adjancies of fip %s %s" % \
                              (vertex['vertex_type'], vertex['uuid']))
            return oper
        intf_details = inspect_h.get_intf_details(vmi_id=vmi_uuid)
        intf_rec = intf_details['ItfResp']['itf_list'][0]
        oper['interface'] = intf_rec

        match = False
        fip_list = intf_rec['fip_list']
        for fip in fip_list:
            if fip['ip_addr'] == self.floating_ip_address:
                match = True
                fip_vrf = fip['vrf_name']
                fip_address = fip['ip_addr']
                pstr = "FIP address %s is found in the interface rec %s" % \
                       (self.floating_ip_address, intf_rec['name'])
                self.logger.debug(pstr)
                print pstr
                break
        if not match:
            pstr = "fip address %s is not found in the interface rec %s" % \
                   (self.floating_ip_address, intf_rec['name'])
            self.logger.error(pstr)
            print pstr
            return oper

        # Get routing entry
        (check, route) = inspect_h.is_prefix_exists(fip_vrf, prefix=fip_address)
        oper['route'] = route
        if check is True:
            nh_list = route['path_list']
            if nh_list:
                print "Agent got nh for %s" % (fip_address)
        else:
            print "Agent Error doesn't have route for %s" % (fip_address)
        return oper

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for FIP', add_help=True)
    parser.add_argument('--floating_ip_address', help='Floating ip address to debug')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vFIP= debugVertexFIP(**args)
    #context = vFIP.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vFIP)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json()
    vP.convert_to_file_structure()
