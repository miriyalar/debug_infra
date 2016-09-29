import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
import debugvmi

class debugVertexIP(baseVertex):
    vertex_type = 'instance-ip'

    def __init__(self, **kwargs):
        self.dependant_vertexes = [debugvmi.debugVertexVMI]
        self.instance_ip_address = kwargs.get('instance_ip_address', None)
        self.ip_addr = dict()
        virtual_network = kwargs.get('virtual_network', None)
        self.uuid = kwargs.get('uuid', None)
        self.match_kv = {'instance_ip_address': self.instance_ip_address,
                         'uuid': self.uuid}
        if virtual_network and ':' in virtual_network:
            self.match_kv.update({'virtual_network_refs.to': virtual_network.split(':')})
        else:
            self.match_kv.update({'virtual_network_refs.uuid': virtual_network})
        super(debugVertexIP, self).__init__(**kwargs)

    def get_schema(self):
        schema_dict = {
            "virtual-machine-interface": {
                'uuid': 'instance_ip_back_refs',
            },
            "virtual-machine": {
                'uuid': 'virtual_machine_interface_back_refs.instance_ip_back_refs',
                'display_name': 'virtual_machine_interface_back_refs.instance_ip_back_refs'
            }
        }
        return schema_dict

    def process_self(self, vertex):
        vertex_type = vertex['vertex_type']
        if not self.instance_ip_address:
            instance_ip_address = self.get_attr('instance_ip_address', vertex)[0]
        else:
            instance_ip_address = self.instance_ip_address
        self.ip_addr[vertex['uuid']] = instance_ip_address

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
        instance_ip_address = self.ip_addr[vertex['uuid']]
        # Need to get the virtual-machine-interface record from the agent
        vmis = list()
        adjacency_type='virtual-machine-interface'
        adjacency_list = inspect_h.get_adjacencies(uuid=vertex['fq_name'],
                                                   adjacency_type=adjacency_type)
        for adjacency in adjacency_list:
            if adjacency[0] == adjacency_type:
                vmis.append(adjacency[1])

        if not vmis:
            self.logger.error("Agent Error, interface is not found in the adjancies of ip %s %s" % \
                              (vertex['vertex_type'], vertex['uuid']))
            return oper
        for vmi in vmis:
            # Need to do the WA of getting UUID from fqname since agent
            # introspect for intf details doesnt accept fq_name
            vmi_uuid = self.config.get_fqname_to_id(obj_type='virtual-machine-interface',
                                                    fq_name=vmi)
            intf_details = inspect_h.get_intf_details(vmi_id=vmi_uuid)
            intf_rec = intf_details['ItfResp']['itf_list'][0]
            oper['interface'] = intf_rec

            ip_address = [oper['interface']['ip_addr']]
            ip_address.extend(oper['interface']['fixed_ip4_list'] or [])
            ip_address.extend([oper['interface']['ip6_addr']] or [])
            if instance_ip_address in ip_address:
                pstr = "IP address %s is found in the interface rec %s" % \
                       (instance_ip_address, intf_rec['name'])
                self.logger.info(pstr)
                print pstr
            else:
                pstr = "IP address %s is NOT found in the interface rec %s" % \
                       (instance_ip_address, intf_rec['name'])
                self.logger.error(pstr)
                print pstr
                return oper

        # Get routing entry
        (check, route) = inspect_h.is_prefix_exists(intf_rec['vrf_name'],
                                                    prefix=instance_ip_address)
        oper['route'] = route
        if check is True:
            nh_list = route['path_list']
            if nh_list:
                print "Agent got nh for %s" % (instance_ip_address)
        else:
            print "Agent Error doesn't have route for %s" % (instance_ip_address)
        return oper

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for IIP', add_help=True)
    parser.add_argument('--instance_ip_address', help='Instance ip address to debug')
    parser.add_argument('--virtual_network', help='Virtual network uuid')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vIIP= debugVertexIP(**args)

    #context = vIIP.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vIIP)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_based_on_uuid( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1',context, False)
    #vP.print_object_catalogue(context, False)
    #vP.print_visited_vertexes_inorder(context)
    vP.convert_json()

