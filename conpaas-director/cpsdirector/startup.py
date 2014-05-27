"""
    cpsdirector.startup
    ===================

    ConPaaS director: start virtual machines for each service

"""

import os.path
import simplejson
from conpaas.core import iaas
from conpaas.core.misc import file_get_contents
from cpsdirector.common import config_parser
from cpsdirector.common import log
from cpsdirector.x509cert import generate_certificate
from flask import jsonify, request, g
import time

class Startup(object):

    def __init__(self, appid):
        self.__vmid = 0
        self.__appid = appid

        self.__available_clouds = []
        self.__default_cloud = None
        if config_parser.has_option('iaas', 'DRIVER'):
            self.__default_cloud = iaas.get_cloud_instance(
                        'iaas',
                       config_parser.get('iaas', 'DRIVER').lower(),
                       config_parser)
            self.__available_clouds.append(self.__default_cloud)

	log("[startup init] cert_dir " + config_parser.get('conpaas','CERT_DIR'))


	cloud = self.__default_cloud.get_cloud_type()
	cloud_name = 'iaas'

        user_id = str(g.user.uid)
        service_id = "0"
        cert_dir = config_parser.get('conpaas', 'CERT_DIR')

        conpaas_home = config_parser.get('conpaas', 'CONF_DIR')

        cloud_scripts_dir = os.path.join(conpaas_home, 'scripts', 'cloud')
        init_scripts_dir = os.path.join(conpaas_home, 'scripts', 'init')
        director = config_parser.get('director', 'DIRECTOR_URL')
        init_cfg_dir = os.path.join(conpaas_home, 'config', 'init')

        # Values to be passed to the context file template
        tmpl_values = {}

        # Get contextualization script for the cloud
        try:
            tmpl_values['cloud_script'] = file_get_contents(
                os.path.join(cloud_scripts_dir, cloud))
        except IOError:
            tmpl_values['cloud_script'] = ''

        # Get cloud config values from director.cfg
        cloud_sections = ['iaas']
        if config_parser.has_option('iaas', 'OTHER_CLOUDS'):
            cloud_sections.extend(
                [cloud_name for cloud_name
                 in config_parser.get('iaas', 'OTHER_CLOUDS').split(',')
                 if config_parser.has_section(cloud_name)])

        def __extract_cloud_cfg(section_name):
            tmpl_values['cloud_cfg'] += "["+section_name+"]\n"
            for key, value in config_parser.items(section_name):
                tmpl_values['cloud_cfg'] += key.upper() + " = " + value + "\n"

        tmpl_values['cloud_cfg'] = ''
        for section_name in cloud_sections:
            __extract_cloud_cfg(section_name)

        # Get manager config file
        init_cfg = file_get_contents(
            os.path.join(init_cfg_dir, 'default-init.cfg'))

        # Get manager setup file
        init_setup = file_get_contents(
            os.path.join(init_scripts_dir, 'init-setup'))

        tmpl_values['init_setup'] = init_setup.replace('%DIRECTOR_URL%',
                                                       director)


        # Modify manager config file setting the required variables
        init_cfg = init_cfg.replace('%DIRECTOR_URL%', director)
	service_name = "init"
	init_cfg = init_cfg.replace('%CONPAAS_SERVICE_TYPE%', service_name)

        init_cfg = init_cfg.replace('%CLOUD_NAME%', cloud_name);
        cloud = self.get_cloud_by_name(cloud_name)

        # OpenNebula, EC2. etc
        init_cfg = init_cfg.replace('%CLOUD_TYPE%',
                config_parser.get(cloud_name, 'DRIVER'))  

        if config_parser.has_option(cloud_name, 'INST_TYPE'):
            init_cfg = init_cfg.replace('%CLOUD_MACHINE_TYPE%',
                    config_parser.get(cloud_name, 'INST_TYPE'))


	init_cfg = init_cfg.replace('%CONPAAS_USER_ID%', user_id)
	init_cfg = init_cfg.replace('%CONPAAS_APP_ID%', self.__appid)
	
        tmpl_values['init_cfg'] = init_cfg

        # Add default manager startup script
        tmpl_values['init_start_script'] = file_get_contents(
            os.path.join(init_scripts_dir, 'default-init-start'))

        init_cert = generate_certificate(cert_dir, user_id, service_id,
					"init",
					"info@conpaas.eu",
					"ConPaaS",
					"Contrail")

        tmpl_values['init_certs_cert'] = init_cert['cert']
        tmpl_values['init_certs_key'] = init_cert['key']
        tmpl_values['init_certs_ca_cert'] = init_cert['ca_cert']
	self.__initial_ctx =  """%(cloud_script)s

cat <<EOF > /tmp/cert.pem
%(init_certs_cert)s
EOF

cat <<EOF > /tmp/key.pem
%(init_certs_key)s
EOF

cat <<EOF > /tmp/ca_cert.pem
%(init_certs_ca_cert)s
EOF

%(init_setup)s

cat <<EOF > $ROOT_DIR/config.cfg
%(cloud_cfg)s
%(init_cfg)s
EOF

%(init_start_script)s""" % tmpl_values

	log ("Initial context is " + self.__initial_ctx)
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
            
