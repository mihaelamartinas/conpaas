'''
Created on Jan 21, 2011

@author: ielhelw
'''

import urlparse

from libcloud.types import Provider, NodeState
from libcloud.providers import get_driver
from libcloud.base import NodeImage
from libcloud.drivers.opennebula import OpenNebulaNodeDriver
from libcloud.drivers.ec2 import EC2NodeDriver

import libcloud.security
libcloud.security.VERIFY_SSL_CERT = False


class IaaSClient:
  RUNNING = NodeState.RUNNING
  REBOOTING = NodeState.REBOOTING
  TERMINATED = NodeState.TERMINATED
  PENDING = NodeState.PENDING
  UNKNOWN = NodeState.UNKNOWN
  
  def __config_opennebula(self, iaas_config):
    if not iaas_config.has_option('iaas', 'OPENNEBULA_URL'): raise Exception('Configuration error: [iaas] OPENNEBULA_URL not set')
    if not iaas_config.has_option('iaas', 'OPENNEBULA_USER'): raise Exception('Configuration error: [iaas] OPENNEBULA_USER not set')
    if not iaas_config.has_option('iaas', 'OPENNEBULA_PASSWORD'): raise Exception('Configuration error: [iaas] OPENNEBULA_PASSWORD not set')
    if not iaas_config.has_option('iaas', 'OPENNEBULA_IMAGE_ID'): raise Exception('Configuration error: [iaas] OPENNEBULA_IMAGE_ID not set')
    if not iaas_config.has_option('iaas', 'OPENNEBULA_SIZE_ID'): raise Exception('Configuration error: [iaas] OPENNEBULA_SIZE_ID not set')
    if not iaas_config.has_option('iaas', 'OPENNEBULA_NETWORK_ID'): raise Exception('Configuration error: [iaas] OPENNEBULA_NETWORK_ID not set')
    if not iaas_config.has_option('iaas', 'OPENNEBULA_NETWORK_GATEWAY'): raise Exception('Configuration error: [iaas] OPENNEBULA_NETWORK_GATEWAY not set')
    
    parsed = urlparse.urlparse(iaas_config.get('iaas', 'OPENNEBULA_URL'))
    self.scheme = parsed.scheme
    self.host = parsed.hostname
    self.port = parsed.port
    self.path = parsed.path
    self.username = iaas_config.get('iaas', 'OPENNEBULA_USER')
    self.password = iaas_config.get('iaas', 'OPENNEBULA_PASSWORD')
    
    self.img_id = iaas_config.get('iaas', 'OPENNEBULA_IMAGE_ID')
    self.size_id = iaas_config.get('iaas', 'OPENNEBULA_SIZE_ID')
    
    self.on_ex_network_id = iaas_config.get('iaas', 'OPENNEBULA_NETWORK_ID')
    self.on_ex_network_gateawy = iaas_config.get('iaas', 'OPENNEBULA_NETWORK_GATEWAY')
    
    ONDriver = get_driver(Provider.OPENNEBULA)
    self.driver = ONDriver(self.username, secret=self.password, secure=(self.scheme == 'https'), host=self.host, port=self.port)
  
  def __config_ec2(self, iaas_config):
    if not iaas_config.has_option('iaas', 'EC2_USER'): raise Exception('Configuration error: [iaas] EC2_USER not set')
    if not iaas_config.has_option('iaas', 'EC2_PASSWORD'): raise Exception('Configuration error: [iaas] EC2_PASSWORD not set')
    if not iaas_config.has_option('iaas', 'EC2_IMAGE_ID'): raise Exception('Configuration error: [iaas] EC2_IMAGE_ID not set')
    if not iaas_config.has_option('iaas', 'EC2_SIZE_ID'): raise Exception('Configuration error: [iaas] EC2_SIZE_ID not set')
    
    if not iaas_config.has_option('iaas', 'EC2_SECURITY_GROUP_NAME'): raise Exception('Configuration error: [iaas] EC2_SECURITY_GROUP_NAME not set')
    if not iaas_config.has_option('iaas', 'EC2_KEY_NAME'): raise Exception('Configuration error: [iaas] EC2_KEY_NAME not set')
    
    self.username = iaas_config.get('iaas', 'EC2_USER')
    self.password = iaas_config.get('iaas', 'EC2_PASSWORD')
    
    self.ec2_ex_securitygroup = iaas_config.get('iaas', 'EC2_SECURITY_GROUP_NAME')
    self.ec2_ex_keyname = iaas_config.get('iaas', 'EC2_KEY_NAME')
    
    self.img_id = iaas_config.get('iaas', 'EC2_IMAGE_ID')
    self.size_id = iaas_config.get('iaas', 'EC2_SIZE_ID')
    
    EC2Driver = get_driver(Provider.EC2_US_EAST)
    self.driver = EC2Driver(self.username, self.password)
  
  def __setdriver(self, iaas_config):
    if not iaas_config.has_option('iaas', 'DRIVER'): raise Exception('Configuration error: [iaas] DRIVER not set')
    drivername = iaas_config.get('iaas', 'DRIVER')
    if drivername == 'OPENNEBULA':
      self.__config_opennebula(iaas_config)
    elif drivername == 'EC2':
      self.__config_ec2(iaas_config)
  
  def __init__(self, iaas_config):
    self.__setdriver(iaas_config)
  
  def listVMs(self):
    nodes = self.driver.list_nodes()
    vms = {}
    for i in nodes:
      vms[i.id] = {'id': i.id,
        'state': i.state,
        'name': i.name,
        'ip': i.public_ip[0]}
    return vms
  
  def getVMInfo(self, vm_id):
    return self.listVMs()[vm_id]
  
  def newInstance(self):
    size = [ i for i in self.driver.list_sizes() if i.id == self.size_id ][0]
    img = NodeImage(self.img_id, '', None)
    kwargs = {'size': size,
              'image': img
              }
    if isinstance(self.driver, OpenNebulaNodeDriver):
      kwargs['ex_network_id'] = self.on_ex_network_id
      kwargs['ex_network_gateawy'] = self.on_ex_network_gateawy
    if isinstance(self.driver, EC2NodeDriver):
      kwargs['ex_securitygroup'] = self.ec2_ex_securitygroup
      kwargs['ex_keyname'] = self.ec2_ex_keyname
      kwargs['ex_userdata'] = '''#!/bin/bash
wget -P /root/ http://hppc644.few.vu.nl/contrail/ConPaaSWeb.tar.gz
wget -P /root/ http://hppc644.few.vu.nl/contrail/agent-start
wget -P /root/ http://hppc644.few.vu.nl/contrail/agent-stop

chmod 755 /root/agent-start
chmod 755 /root/agent-stop

/root/agent-start
'''
    
    node = self.driver.create_node(name='conpaas', **kwargs)
    return {'id': node.id,
        'state': node.state,
        'name': node.name,
        'ip': node.public_ip[0]}
  
  def killInstance(self, vm_id):
    nodes = self.driver.list_nodes()
    for i in nodes:
      if i.id == vm_id:
        return self.driver.destroy_node(i)
    return False
