import traceback
import lxml.etree as etree

from sapi import app
from sapi.utils import traceback_enable
#xml configration string
from sapi.tor.h3c_xml import *

def interface_info(_connect_tor):
    interface = []
    def replace_ifindex(s):
        s1 = s.replace('<IfIndex>', '')
        return s1.replace('</IfIndex>', '')
    def replace_name(s):
        s1 = s.replace('<Name>', '')
        return s1.replace('</Name>', '')
    with _connect_tor as m:
        try:
            configstr = RETRIEVE_ALL_INTERFACES
            ret = m.get(filter=('subtree', configstr))
            x = etree.fromstring(ret.data_xml)
            lines = etree.tostring(x, pretty_print = True).split('\n')
            _lines = [line.strip() for line in lines]
            lines = [line for line in _lines if line.startswith('<IfIndex>') or line.startswith('<Name>')]
            interface = [(replace_ifindex(lines[2*i]), replace_name(lines[2*i+1])) \
                    for i in range(len(lines)/2)]
        except:
            pass
        return interface

def special_interface_info(_connect_tor, if_index):
    with _connect_tor as m:
        try:
            configstr = RETRIEVE_SPECIAL_INTERFACES.format(if_index = if_index)
            ret = m.get(filter=('subtree', configstr))
            print ret
        except:
            pass

def get_tunnels(_connect_tor):
    tunnels = []
    def replace_ifindex(s):
        s1 = s.replace('<IfIndex>', '')
        return s1.replace('</IfIndex>', '')
    def replace_id(s):
        s1 = s.replace('<ID>', '')
        return s1.replace('</ID>', '')
    with _connect_tor as m:
        try:
            configstr = RETRIEVE_TUNNELS
            ret = m.get(filter=('subtree', configstr))
            x = etree.fromstring(ret.data_xml)
            lines = etree.tostring(x, pretty_print = True).split('\n')
            _lines = [line.strip() for line in lines]
            lines = [line for line in _lines if line.startswith('<ID>') or line.startswith('<IfIndex>')]
            tunnels = [(replace_id(lines[2*i]), replace_ifindex(lines[2*i+1])) \
                    for i in range(len(lines)/2)]
        except:
            pass
        return tunnels

def get_avaliable_tunnel_id(_connect_tor):
    id = -1
    def replace_id(s):
        s1 = s.replace('<ID>', '')
        return s1.replace('</ID>', '')
    with _connect_tor as m:
        try:
            configstr = RETRIEVE_AVAILABLE_TUNNEL_ID
            ret = m.get(filter=('subtree', configstr))
            x = etree.fromstring(ret.data_xml)
            lines = etree.tostring(x, pretty_print = True).split('\n')
            _lines = [line.strip() for line in lines]
            for line in _lines:
                if line.startswith('<ID>'):
                    id = replace_id(line)
        except:
            pass
        return id

class Base(object):
    def __init__(self, conn):
        self.conn = conn

    def _connect_tor(self):
        return self.conn

    def _check_response(self, ret, op):
        response = ret.xml
        if 'ok' in response:
            return True
        else:
            return False

class VSI(Base):
    def __init__(self, conn, name):
        super(VSI, self).__init__(conn)
        self._name = name

    def __repr__(self):
        return "<VSI: %s>" %(self._name)

    @property
    def name(self):
        return self._name

    @property
    def __delete_xml(self):
        return VSI_OPERATION.format(operation="delete", vsiname=self._name)

    @property
    def __create_xml(self):
        return VSI_OPERATION.format(operation="merge", vsiname=self._name)

    @traceback_enable
    def create(self):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running', config=self.__create_xml)
            self._check_response(ret, 'create_vsi')

    @traceback_enable
    def delete(self):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running', config=self.__delete_xml)
            self._check_response(ret, 'delete_vsi')

class TUNNEL(Base):
    def __init__(self, conn, tunnel_id, src_addr='', dst_addr=''):
        super(TUNNEL, self).__init__(conn)
        self.tunnel_id = tunnel_id
        self.src_addr = src_addr
        self.dst_addr = dst_addr

    @property
    def create_xml(self):
        return CREATE_TUNNEL.format(
                tunnel_id = self.tunnel_id,
                src_addr = self.src_addr,
                dst_addr = self.dst_addr)

    @property
    def delete_xml(self):
        return DELETE_TUNNEL.format(
                tunnel_id = self.tunnel_id)

    @traceback_enable
    def create(self):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config = self.create_xml)
            self._check_response(ret, 'create_tunnel')

    @traceback_enable
    def delete(self):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config = self.delete_xml)
            self._check_response(ret, 'delete_tunnel')


class VXLAN(Base):
    def __init__(self, conn, vxlan_id, vsi_name=''):
        super(VXLAN, self).__init__(conn)
        self.vxlan_id = vxlan_id
        self._vsi_name = vsi_name

    def __repr__(self):
        return "<VXLAN: %s %s>" %(self.vxlan_id, self.vsi_name)

    @property
    def vsi_name(self):
        return self._vsi_name

    @vsi_name.setter
    def vsi_name(self, vsi_name):
        self._vsi_name = vsi_name

    @property
    def create_xml(self):
        return CREATE_VXLAN_VSI.format(vxlanid = self.vxlan_id,
                                       vsiname = self.vsi_name)

    @property
    def delete_xml(self):
        return DELETE_VXLAN.format(vxlanid = self.vxlan_id)

    def edit_tunnel_xml(self, tunnel_id):
        return EDIT_VXLAN_TUNNEL.format(vxlanid = self.vxlan_id,
                                        tunnelid = tunnel_id)

    @traceback_enable
    def create(self):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config = self.create_xml)
            self._check_response(ret, 'create_vxlan_with_vsi')

    @traceback_enable
    def delete(self):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config = self.delete_xml)
            self._check_response(ret, 'delete_vxlan')

    @traceback_enable
    def connect_vxlan_with_tunnel(self, tunnel_id):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config = self.edit_tunnel_xml(tunnel_id))
            self._check_response(ret, 'connect_vxlan_with_tunnel')

class Interface(Base):
    def __init__(self, conn, if_index):
        super(Interface, self).__init__(conn)
        self.if_index = if_index

    def __repr__(self):
        return "<Interface : %d>" %(self.if_index)

    #link_type 1: access port, 2: trunk port
    def port_trunk_xml(self, link_type=1):
        return INTERFACE_VLAN_TRUNK_ACCESS.format(if_index = self.if_index,
                                           link_type = link_type)

    def port_permit_vlan_xml(self, vlan_range):
        return INTERFACE_TRUNK_PERMIT_VLAN.format(vlan_list = vlan_range,
                                                if_index = self.if_index)

    def port_service_create_xml(self, service_id, s_vid):
        return CREATE_SERVICE.format(service_id = service_id,
                                     if_index = self.if_index,
                                     s_vid = s_vid)

    def port_service_delete_xml(self, service_id):
        return DELETE_SERVICE.format(service_id = service_id,
                                     if_index = self.if_index)

    def port_ac_create_xml(self, service_id, vsi_name):
        return CREATE_AC.format(if_index = self.if_index,
                                service_id = service_id,
                                vsi_name = vsi_name)

    def port_ac_delete_xml(self, service_id):
        return DELETE_AC.format(if_index = self.if_index,
                                service_id = service_id)

    @traceback_enable
    def port_trunk(self):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config=self.port_trunk_xml(link_type=2))
            self._check_response(ret, 'trunk_interface')

    @traceback_enable
    def port_access(self):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config=self.port_trunk_xml(link_type=1))
            self._check_response(ret, 'access_interface')

    #vlan range permit on interface, eg: "1" or "1,3,20"
    @traceback_enable
    def port_trunk_permit_vlan(self, vlan_range="1"):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config=self.port_permit_vlan_xml(vlan_range))
            self._check_response(ret, 'interface_permit_vlan_range')

    @traceback_enable
    def port_service_create(self, service_id, s_vid):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config=self.port_service_create_xml(service_id, s_vid))
            self._check_response(ret, 'interface_service_create')

    @traceback_enable
    def port_service_delete(self, service_id):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config=self.port_service_delete_xml(service_id))
            self._check_response(ret, 'interface_service_delete')

    @traceback_enable
    def port_ac_create(self, service_id, vsi_name):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config=self.port_ac_create_xml(service_id, vsi_name))
            self._check_response(ret, 'interface_ac_create')

    @traceback_enable
    def port_ac_delete(self, service_id):
        with self._connect_tor() as m:
            ret = m.edit_config(target='running',
                                config=self.port_ac_delete_xml(service_id))
            self._check_response(ret, 'interface_ac_delete')

if __name__ == '__main__':
    #vxlan 300 => vlan 3 <=> service instance 3
    #vsi_name = 'vsitmp'
    #i = Interface(169)
    #v = VXLAN(300)

    #vsi = VSI(vsi_name)
    #vsi.create()
    #v.vsi_name = vsi_name
    #v.create()
    #v.connect_vxlan_with_tunnel(1)

    #i.port_trunk()
    #i.port_trunk_permit_vlan(vlan_range="1,3,5")
    #i.port_service_create(3, 3)
    #i.port_ac_create(3, v.vsi_name)

    #get_tunnels()
    #special_interface_info(31645)
    ret = interface_info()
    for interface in ret:
        print "if_index: %s, name: %s" %(interface[0], interface[1])
