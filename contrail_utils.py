import pdb
import json
from contrail_uve import ContrailUVE
from contrail_api import ContrailApi

class ContrailUtils(object):
    def __init__(self, token=None):
        self.token = token

    @staticmethod
    def add_unique_object_in_object_list(object_list, obj, key_field):
        found_obj = False
        for object_item in object_list:
            if obj[key_field] == object_item[key_field]:
                found_obj = True
        if not found_obj:
            object_list.append(obj)

    def check_for_vm_vmi_in_context(self, contrail_info, context_path, config_ip, config_port, analytics_ip, uve_obj, config_api):
        #Check if there is VM/VMI in the context Path
        for element in context_path:
            if element['type'] == 'virtual-machine':
                #vm_uuid = element['uuid']
                fq_name = element['fq_name']
                contrail_info.update(self.get_contrail_vm_info(fq_name, config_ip=config_ip, config_port=config_port,
                                                                        analytics_ip=analytics_ip))
                return True 
            elif  element['type'] == 'virtual-machine-interface':
                vmi_obj = uve_obj.get_object(element['fq_name'], "virtual-machine-interface", select_fields = ['UveVMInterfaceAgent.vm_uuid'])
                vm_uuid = vmi_obj['UveVMInterfaceAgent.vm_uuid']
                fq_name = ':'.join(config_api.post("id-to-fqname", {"uuid": vm_uuid})['fq_name'])
                contrail_info.update(self.get_contrail_vm_info(fq_name, config_ip=config_ip, config_port=config_port,
                                                                        analytics_ip=analytics_ip))
                return True
        return False 

    def get_contrail_info(self, uuid, uuid_type, config_ip='127.0.0.1', config_port='8082', **kwargs):
        _agent_schema_dict = {
            'virtual-network' : 'virtual_machine_interface_back_refs.virtual_machine_refs',
            'floating-ip': 'virtual_machine_interface_refs.virtual_machine_refs',
            'security-group' : 'virtual_machine_interface_back_refs.virtual_machine_refs',
            'virtual-machine-interface': 'virtual_machine_refs',
            'instance-ip': 'virtual_machine_interface_refs.virtual_machine_refs'
        }

        fq_name = kwargs.get('fq_name', None)
        contrail_info = {'vrouter': [], 'control': []}
        analytics_ip = kwargs.get('analytics_ip', None)
        analytics_port = kwargs.get('analytics_port', '8081')
        #Could be a list of dict
        context_path = kwargs.get('context_path', [])
 
        if not analytics_ip:
            contrail_control_nodes = self.get_contrail_nodes(config_ip=config_ip, config_port=config_port)
            analytics_ip = contrail_control_nodes['analytics_nodes'][0]['ip_address']
        uve_obj = ContrailUVE(ip=analytics_ip, port=analytics_port)
        if uuid_type == "virtual-machine":
            vm_uuid = uuid
        else:
            #generic code to get associated Vrouter and control objects.
            where = 'uuid==%s' %(uuid)
            config_api = ContrailApi(ip=config_ip, port=config_port, token=self.token)
            if self.check_for_vm_vmi_in_context(contrail_info, context_path, config_ip, config_port, analytics_ip, uve_obj, config_api):
                return contrail_info
            #there was no VM/VMI object in the context path
            #so return info for all the VM's.
            object_name = uuid_type.replace('_', '-')                
            schema_to_use = _agent_schema_dict[object_name] 
            vm_objs = config_api.get_object_deep(object_name, schema_to_use, where = where)
            for vm in vm_objs:
                fq_name = ':'.join(vm.values()[0]['fq_name'])
                tmp_contrail_info = self.get_contrail_vm_info(fq_name, config_ip=config_ip, config_port=config_port,
                                                                       analytics_ip=analytics_ip, config_api=config_api)
                vrouter_objs = tmp_contrail_info['vrouter']
                control_objs = tmp_contrail_info['control']
                for vrouter_obj in vrouter_objs:
                    ContrailUtils.add_unique_object_in_object_list(contrail_info['vrouter'], vrouter_obj, 'ip_address')    
                for control_obj in control_objs:
                    ContrailUtils.add_unique_object_in_object_list(contrail_info['control'], control_obj, 'ip_address')
            return contrail_info
	#Should we move this to each of the cases.
        if not fq_name:
            fq_name = vm_uuid
        contrail_info = self.get_contrail_vm_info(fq_name, config_ip=config_ip, config_port=config_port,
                                                           analytics_ip=analytics_ip)
        return contrail_info


    def get_contrail_vmi_info(self, fq_name, config_ip='127.0.0.1', config_port='8082', **kwargs):
        contrail_info = {'vrouter': [], 'control': []}
        analytics_ip = kwargs.get('analytics_ip', None)
        analytics_port = kwargs.get('analytics_port', '8081')
        config_api = kwargs.get('config_api', None)
        try:
            if not analytics_ip:
                contrail_nodes = self.get_contrail_nodes(config_ip=config_ip, config_port=config_port, config_api=config_api)
                analytics_ip = contrail_nodes['analytics_nodes'][0]['ip_address']
            uve_obj = ContrailUVE(ip=analytics_ip, port=analytics_port)
            vmi_obj = uve_obj.get_object(fq_name, "virtual-machine-interface", select_fields = ['UveVMInterfaceAgent.vm_uuid'])
            vm_uuid = vmi_obj['UveVMInterfaceAgent.vm_uuid']
            contrail_info = self.get_contrail_vm_info(vm_uuid, config_ip=config_ip, config_port=config_port,
                                                               analytics_ip=analytics_ip, config_api=config_api)
            return contrail_info
        except:
            return contrail_info


    def get_contrail_vm_info(self, fq_name, config_ip='127.0.0.1', config_port='8082', **kwargs):
        # vrouter['hostname'], vrouter['ip_address'], control['hostname'], control['ip_address']
        contrail_info = {'vrouter': [], 'control': []}
        analytics_ip = kwargs.get('analytics_ip', None)
        analytics_port = kwargs.get('analytics_port', '8081')
        config_api = kwargs.get('config_api', None)
        try:
            if not analytics_ip:
                contrail_nodes = self.get_contrail_nodes(config_ip=config_ip, config_port=config_port, 
                                                                  config_api=config_api)
                analytics_ip = contrail_nodes['analytics_nodes'][0]['ip_address']
            uve_obj = ContrailUVE(ip=analytics_ip, port=analytics_port)        
            vrouter_obj = uve_obj.get_object(fq_name, "virtual-machine", select_fields = ['UveVirtualMachineAgent.vrouter'])
            vrouter = {}
            vrouter_name = vrouter_obj['UveVirtualMachineAgent.vrouter']
            vrouter['hostname'] = vrouter_name
            peer_list = uve_obj.get_object(vrouter_name ,"vrouter", select_fields = ['VrouterAgent.xmpp_peer_list', 
                                                                                     'VrouterAgent.self_ip_list',
                                                                                     'VrouterAgent.sandesh_http_port'])
            vrouter['ip_address'] = peer_list['VrouterAgent.self_ip_list'][0]
            vrouter['sandesh_http_port'] = peer_list['VrouterAgent.sandesh_http_port']
            vrouter['peers'] = []
            contrail_info['vrouter'].append(vrouter)
            xmpp_peer_list = peer_list['VrouterAgent.xmpp_peer_list']
            for peer in xmpp_peer_list:
                control = {}
                control['ip_address'] = peer['ip']
                control['xmpp_status'] = peer['status']
                control['primary'] = peer['primary']
                control['sandesh_http_port'] = '8083'
                contrail_info['control'].append(control)
                vrouter['peers'].append(control)
            return contrail_info
        except:
            return contrail_info


    def get_control_nodes(self, config_ip='127.0.0.1', config_port='8082'):
        contrail_info = self.get_contrail_nodes(config_ip, config_port)
        contrail_info.pop('vrouters')
        return contrail_info

    def get_contrail_nodes(self, config_ip='127.0.0.1', config_port='8082', config_api=None):
        contrail_nodes = {}
        if not config_api:
            config_api = ContrailApi(ip=config_ip, port=config_port, token=self.token)
        global_configs_url = 'http://%s:%s/global-system-configs' % (config_ip, config_port)
        global_configs = config_api.get_object(object_name='', 
                                               url=global_configs_url)
        global_config = config_api.get_object(object_name='', 
                                              url=global_configs['global-system-configs'][0]['href'])['global-system-config']

        config_nodes = global_config['config_nodes']
        contrail_nodes['config_nodes'] = []
        for node in config_nodes:
            config_node = config_api.get_object(object_name='',
                                                url=node['href'])
            cnode = {}
            cnode['ip_address'] = str(config_node['config-node']['config_node_ip_address'])
            cnode['hostname'] = str(config_node['config-node']['name'])
            cnode['port'] = 9100 #For now, hardcoding it to 9100
            contrail_nodes['config_nodes'].append(cnode)

        database_nodes = global_config['database_nodes']
        contrail_nodes['database_nodes'] = []
        for node in database_nodes:
            database_node = config_api.get_object(object_name='',
                                                  url=node['href'])
            dnode = {}
            dnode['ip_address'] = str(database_node['database-node']['database_node_ip_address'])
            dnode['hostname'] = str(database_node['database-node']['name'])
            contrail_nodes['database_nodes'].append(dnode)

        analytics_nodes = global_config['analytics_nodes']
        contrail_nodes['analytics_nodes'] = []
        for node in analytics_nodes:
            analytics_node = config_api.get_object(object_name='',
                                                   url=node['href'])
            anode = {}
            anode['ip_address'] = str(analytics_node['analytics-node']['analytics_node_ip_address'])
            anode['hostname'] = str(analytics_node['analytics-node']['name'])
            anode['port'] = 8081
            contrail_nodes['analytics_nodes'].append(anode)

        virtual_routers = global_config['virtual_routers']
        contrail_nodes['vrouters'] = []
        for node in virtual_routers:
            virtual_router = config_api.get_object(object_name='',
                                                   url=node['href'])
            vnode = {}
            vnode['ip_address'] = str(virtual_router['virtual-router']['virtual_router_ip_address'])
            vnode['hostname'] = str(virtual_router['virtual-router']['name'])
            vnode['sandesh_http_port'] = 8085
            contrail_nodes['vrouters'].append(vnode)

        bgp_routers_url = 'http://%s:%s/bgp-routers?detail=True' % (config_ip, config_port)
        bgp_routers = config_api.get_object(object_name='', url=bgp_routers_url)['bgp-routers']
        contrail_nodes['control_nodes'] = []
        for bgp_router in bgp_routers:
            controller = config_api.get_object(object_name='', url=bgp_router['href'])
            if controller['bgp-router']['bgp_router_parameters']['vendor'] == 'contrail':
                cnode = {}
                cnode['ip_address'] = str(controller['bgp-router']['bgp_router_parameters']['address'])
                cnode['hostname'] = str(controller['bgp-router']['name'])
                cnode['sandesh_http_port'] = 8083
                contrail_nodes['control_nodes'].append(cnode)
        return contrail_nodes



if __name__ == "__main__":
    #roles = ContrailUtils.get_contrail_nodes(config_ip='10.84.17.5', config_port='8082')
    #vm_info = ContrailUtils.get_contrail_vm_info('9f838303-7d84-44c4-9aa3-b34a3e8e56b1', 
    #                                             config_ip='10.84.17.5', config_port='8082',
    #                                             analytics_ip='10.84.17.5', analytics_port='8081')
    #contrail_info = ContrailUtils.get_contrail_vm_info('9f838303-7d84-44c4-9aa3-b34a3e8e56b1', config_ip='10.84.17.5')
    import pdb; pdb.set_trace()
    uve_obj = ContrailUtils.get_uve_obj(ContrailApi(ip='10.84.17.5', port='8082'))
    contrail_info = ContrailUtils.get_contrail_vmi_info('default-domain:admin:060c2b5f-d43a-4ea5-844d-393819ff36fd', 
                                                        config_ip='10.84.17.5', config_port='8082')
    pdb.set_trace()

