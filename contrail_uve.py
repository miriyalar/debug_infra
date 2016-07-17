#!/bin/python
import pdb
import logger
import pprint
import json
import re
from urlparse import urlparse
from contrail_api_con import ContrailApiConnection

class ContrailUVE:
    def __init__(self, ip = "127.0.0.1", port = "8081", token=None):
        self.log = logger.getLogger(logger_name=self.__class__.__name__)
        token_header = {'X-AUTH-TOKEN': token} if token else {}
        self._api_con = ContrailApiConnection(ip=ip, port=port,
                                              headers=token_header)

    def get_object_deep(self, object_name, obj_type, select_fields = []):
        pass

    def get_object(self, object_name, obj_type, select_fields = []):
        uve_path = "analytics/uves/" + obj_type
        object_path = uve_path + "/" +  object_name + "?flat"
        obj = self._api_con.get(object_path)
        ret_dict = {}

        if len(select_fields) <= 0:
            return obj

        for element in select_fields:
            element_list = element.split('.')
            tmp_obj = obj
            not_found = False
            for level in element_list:
                if level in tmp_obj:
                    tmp_obj = tmp_obj[level]
                else:
                    pstr = 'Error: Object %s, %s not found, trying to get %s' % \
                           (obj_type, object_name, level)
                    print pstr
                    not_found = True
                    break;
            if not_found == False:
                ret_dict[element] = tmp_obj                    

        return ret_dict



def get_vm_info(uuid = ""):
    uve_obj = ContrailUVE(ip = "127.0.0.1", port = 8081)
    vrouter = uve_obj.get_object( '9f838303-7d84-44c4-9aa3-b34a3e8e56b1' ,"virtual-machine", select_fields = ['UveVirtualMachineAgent.vrouter'])
    xmpp_peer_list =  uve_obj.get_object( 'a3s19' ,"vrouter", select_fields = ['VrouterAgent.xmpp_peer_list'])

    pdb.set_trace()


if __name__ == "__main__":
    pdb.set_trace()
    #first test to try out what needs to be done
#    test_first_floating_ip('7.7.7.3')
#    optimize_floating_ip_de_ref(given_ip= '7.7.7.3')
    #debug_floating_ip('7.7.7.3')
    get_vm_info(uuid = "")
