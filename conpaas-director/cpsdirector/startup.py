"""
    cpsdirector.startup
    ===================

    ConPaaS director: start virtual machines for each service

"""

from conpaas.core import iaas
from cpsdirector.common import config_parser
from cpsdirector.common import log
from cpsdirector.x509cert import generate_certificate
from flask import jsonify, request, g
import time

class Startup(object):

    def __init__(self):
        self.__vmid = 0

        self.__available_clouds = []
        self.__default_cloud = None
        if config_parser.has_option('iaas', 'DRIVER'):
            self.__default_cloud = iaas.get_cloud_instance(
                        'iaas',
                       config_parser.get('iaas', 'DRIVER').lower(),
                       config_parser)
            self.__available_clouds.append(self.__default_cloud)

	log("[startup init] cert_dir " + config_parser.get('conpaas','CERT_DIR'))
        tmp_cert = generate_certificate(config_parser.get('conpaas','CERT_DIR'),
						str(g.user.uid),
						"initial_connect",
						"tmp",
						"info@conpaas.eu",
                                           	"ConPaaS",
                                           	"Contrail")

	tmpl_values = {}	
	tmpl_values['mngr_certs_cert'] = tmp_cert['cert']
        tmpl_values['mngr_certs_key'] = tmp_cert['key']
        tmpl_values['mngr_certs_ca_cert'] = tmp_cert['ca_cert']

	self.__initial_ctx =  """

	cat <<EOF > /tmp/cert.pem
	%(mngr_certs_cert)s
	EOF
	
	cat <<EOF > /tmp/key.pem
	%(mngr_certs_key)s
	EOF
	
	cat <<EOF > /tmp/ca_cert.pem
	%(mngr_certs_ca_cert)s
	EOF""" % tmpl_values

        if config_parser.has_option('iaas', 'OTHER_CLOUDS'):
            self.__available_clouds.append(iaas.get_clouds(config_parser))
	
	self.__partially_created_nodes = []
	self.ready = []

    def get_cloud_by_name(self, cloud_name):
        """
            @param cloud_name

            @return The cloud object which name is the same as @param name

        """
        try:
            return [ cloud for cloud in self.__available_clouds 
                if cloud.get_cloud_name() == cloud_name ][0]
        except IndexError:
            raise Exception("Unknown cloud: %s. Available clouds: %s" % (
                cloud_name, self.__available_clouds))

    def list_vms(self, cloud=None):
        """Returns an array with the VMs running at the given/default(s) cloud.

           @param cloud (Optional) If specified, this method will return the
                         VMs already running at the given cloud
        """
        if cloud is None:
            cloud = self.__default_cloud

        return cloud.list_vms()


    def start_vm(self, count, appid, cloud=None):
         """
         Creates virtual machines corresponding to future managers and agents

         @param count The number of nodes to be created

         @param test_agent A callback function to test if the agent
                             started correctly in the newly created VM

         @param port The port on which the agent will listen

         @param cloud This function will start new
                       nodes inside cloud, otherwise it will start new nodes
                       inside the default cloud or wherever the controller
                       wants (for now only the default cloud is used)

         @return A list of nodes of type node.ServiceNode
         """

         ready = []
         poll = []
         iteration = 0
         partially_created_nodes = []

         if count == 0:
             return []
	
	 if cloud is None:
	     cloud = self.__default_cloud

         cloud.set_context(self.__initial_ctx)
	

	 log('[start_vm]: length of nodes is %d' %(count))

	 for vm_id in range(0, count):
             name = "conpaas-appid-%s-vmid-%s" % (str(appid), str(vm_id))
             self.__partially_created_nodes += cloud.new_instances(1, name)

	 log('[start_vm]: number of partially created nodes %d' % (len(self.__partially_created_nodes)))


    def delete_vm(self, nodes, cloud):
        for node in nodes:
            cloud.kill_instance(node)


    def wait_for_nodes(self):
        """ Verify if a machine acquired an ip address already or not """
        done = []

        for node in self.__partially_created_nodes:
            refreshed_node_list = self.list_vms(self.get_cloud_by_name(node.cloud_name))

            for refreshed_node in refreshed_node_list:
                if refreshed_node.id == node.id:
                    node.ip = refreshed_node.ip
                    node.private_ip = refreshed_node.private_ip
                    done.append(node)
                    break;

        self.__partially_created_nodes = [node for node in self.__partially_created_nodes if node not in done]

        self.ready += done
       
        return done
            
