import sys
from vertex_print import vertexPrint
from basevertex import baseVertex
from parser import ArgumentParser
from contrail_utils import ContrailUtils
from contrailnode_api import Vrouter

def get_route_uuid(prefix, ri_fqname, vrouters):
    return ':'.join(['route', prefix, ri_fqname] +
                    [vrouter['hostname'] for vrouter in vrouters or []])

class debugVertexRoute(baseVertex):
    vertex_type = 'route'
    non_config_obj = True
    def __init__(self, prefix=None, vn_fqname=None, ri_fqname=None,
                 vrouters=None, **kwargs):
        self.vrouters = vrouters
        self.ri_fqname = ri_fqname
        self.vn_fqname = vn_fqname
        self.prefix = prefix
        self.ri = dict()
        self.match_kv = {'dummy': 'dummy'}
        super(debugVertexRoute, self).__init__(**kwargs)

    def get_schema(self):
        pass

    def locate_obj(self):
        ris = list()
        if self.element is not None:
            self.prefix = self.element['prefix']
            self.ri_fqname = self.element['ri_fqname']
            self.vrouters = self.element['vrouters']
        if not self.ri_fqname:
            ri_objs, dummy = self.config.get_object('virtual-network',
                                   schema_to_use='routing_instances',
                                   where='fqname=%s'%self.vn_fqname)
            for ri_obj in ri_objs or []:
                ris.append(':'.join(ri_obj['routing-instance']['fq_name']))
        else:
            ris = [self.ri_fqname]
        objs = list()
        for ri in ris or []:
            uuid = get_route_uuid(self.prefix, ri, self.vrouters)
            self.ri[uuid] = ri
            objs.append({self.vertex_type: {'ri_fqname': ri,
                                            'uuid': uuid,
                                            'vrouters': self.vrouters}})
        return objs

    def store_config(self, vertex):
        pass

    def get_vrouter_info(self, vertex):
        ri_fqname = self.ri[vertex['uuid']]
        if not self.vn_fqname:
            self.vn_fqname = ri_fqname[:ri_fqname.rfind(':')]
        if not self.vrouters:
            vn_uuid = self.config.get_fqname_to_id(obj_type='virtual-network',
                                                   fq_name=self.vn_fqname)
            contrail_info = ContrailUtils(token=self.token).get_contrail_info(
                                          vn_uuid, 'virtual-network',
                                          config_ip=self.config_ip,
                                          config_port=self.config_port,
                                          context_path=self.context.get_path(),
                                          fq_name=self.vn_fqname)
            vrouter = Vrouter(contrail_info['vrouter'])
            self.vrouters = vrouter.get_nodes()
        else:
            vrouter = Vrouter(self.vrouters)
        return vrouter

    def process_self(self, vertex):
        ri_fqname = self.ri[vertex['uuid']]
        control_nodes = set()
        for vrouter in self.vrouters:
            for peer in vrouter['peers']:
                control_nodes.add(peer['ip_address'])
        agent = {}
        agent['oper'] = self.agent_oper_db(self._get_agent_oper_db, vertex)
        self._add_agent_to_context(vertex, agent)
        control = {}
        control['oper'] = self.control_oper_db(self._get_control_oper_db, vertex)
        self._add_control_to_context(vertex, control)

    def _get_agent_oper_db(self, introspect, vertex):
        knh = list()
        (exists, route) = introspect.is_route_exists(self.ri[vertex['uuid']],
                                                    self.prefix)
        if not exists:
            self.logger.warn('Route for %s doesnt exist in VRF %s of agent %s'%(
                          self.prefix, self.ri[vertex['uuid']], introspect._ip))
        (exists, kroute) = introspect.is_kroute_exists(self.prefix,
                                      vrf_fq_name=self.ri[vertex['uuid']])
        if not exists:
            self.logger.warn('Route for %s doesnt exist in VRF %s of kernel %s'%(
                          self.prefix, self.ri[vertex['uuid']], introspect._ip))
        for route in kroute:
            nh = route.get('nh_id')
            if nh:
                knh.extend(introspect.get_knh(route['nh_id']))
        return {'route': route, 'kroute': kroute, 'knh': nh}

    def _get_control_oper_db(self, introspect, vertex):
        (exists, route) = introspect.is_route_exists(self.ri[vertex['uuid']],
                                                    self.prefix)
        if not exists:
            self.logger.warn('Route for %s doesnt exist in VRF %s of control %s'%(
                          self.prefix, self.ri[vertex['uuid']], introspect._ip))
        return {'route': route}

def parse_args(args):
    parser = ArgumentParser(description='Debug utility for Route Verification', add_help=True)
    parser.add_argument('--ri_fqname', help='FQName of the Routing Instance')
    parser.add_argument('--vn_fqname', help='FQName of the Virtual Network')
    parser.add_argument('--prefix', help='Route prefix to verify')
    parser.add_argument('--vrouters', help='List of vrouters to verify')
    return parser.parse_args(args)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    vRoute = debugVertexRoute(**args)
    #context = vSI.get_context()
    #vertexPrint(context, detail=args.detail)
    vP = vertexPrint(vRoute)
    #vP._visited_vertexes_brief(context)
    #vP.print_visited_nodes(context, detail=False)
    #vP.print_object_catalogue(context, False)
    #vP.convert_to_file_structure(context)
    vP.convert_json()
