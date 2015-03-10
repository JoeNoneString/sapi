#!/usr/bin/env python
# encoding: utf-8
from sqlalchemy.orm import exc

from sapi import db
from sapi import utils
from sapi.model import db_constants

UUID_LEN = db_constants.UUID_LEN
OVS_TYPE = db_constants.OVS_TYPE

#neutron network database representation
class SapiProvisionedNets(db.Model):
    __tablename__ = "sapi_provisioned_nets"

    network_id = db.Column(db.String(UUID_LEN), primary_key = True)
    tenant_id = db.Column(db.String(UUID_LEN))
    segmentation_id = db.Column(db.Integer)
    segmentation_type = db.Column(db.String(UUID_LEN))
    admin_state_up = db.Column(db.Integer)
    shared = db.Column(db.Integer)

    def __init__(self, network_id, tenant_id, segmentation_id,
                 segmentation_type, admin_state_up, shared):
        self.network_id = network_id
        self.tenant_id = tenant_id
        self.segmentation_id = segmentation_id
        self.segmentation_type = segmentation_type
        self.admin_state_up = admin_state_up
        self.shared = shared

    def sapi_net_representation(self):
        return {'network_id': self.network_id,
                'tenant_id': self.tenant_id,
                'segmentation_id': self.segmentation_id,
                'segmentation_type': self.segmentation_type,
                'admin_state_up': self.admin_state_up,
                'shared': self.shared}

@utils.traceback_enable
def persistence_nets(net):
    n = SapiProvisionedNets(
            network_id = net['network_id'],
            tenant_id = net['tenant_id'],
            segmentation_id = net['segmentation_id'],
            segmentation_type = net['segmentation_type'],
            admin_state_up = net['admin_state_up'],
            shared = net['shared'])
    db.session.add(n)
    db.session.commit()

@utils.traceback_enable
def delete_nets(tenant_id, network_id):
    SapiProvisionedNets.query.filter_by(
            tenant_id = tenant_id,
            network_id = network_id).delete()
    db.session.commit()

def get_network(network_id):
    try:
        net = SapiProvisionedNets.query.filter_by(
                network_id = network_id).one()
        return net.sapi_net_representation()
    except exc.NoResultFound:
        return None

@utils.traceback_enable
def update_nets(tenant_id, network_id, net):
    SapiProvisionedNets.query.filter_by(
            tenant_id = tenant_id,
            network_id = network_id).update(net)
    db.session.commit()

#neutron subnet database representation
class SapiProvisionedSubnets(db.Model):
    __tablename__ = "sapi_provisioned_subnets"

    subnet_id = db.Column(db.String(UUID_LEN), primary_key=True)
    tenant_id = db.Column(db.String(UUID_LEN))
    network_id = db.Column(db.String(UUID_LEN))
    enable_dhcp = db.Column(db.Integer)
    shared = db.Column(db.Integer)

    def __init__(self, subnet_id, network_id,
            tenant_id, enable_dhcp, shared):
        self.subnet_id = subnet_id
        self.network_id = network_id
        self.tenant_id = tenant_id
        self.enable_dhcp = enable_dhcp
        self.shared = shared

    def sapi_subnet_representation(self):
        return {'subnet_id': self.subnet_id,
                'network_id': self.network_id,
                'tenant_id': self.tenant_id,
                'enable_dhcp': self.enable_dhcp,
                'shared': self.shared}

@utils.traceback_enable
def get_subnet(subnet_id):
    try:
        subnet = SapiProvisionedSubnets.query.filter_by(
                subnet_id = subnet_id).one()
        return subnet.sapi_subnet_representation()
    except exc.NoResultFound:
        return None

@utils.traceback_enable
def persistence_subnets(subnet):
    s = SapiProvisionedSubnets(
            subnet_id = subnet['subnet_id'],
            network_id = subnet['network_id'],
            tenant_id = subnet['tenant_id'],
            enable_dhcp = subnet['enable_dhcp'],
            shared = subnet['shared'])
    db.session.add(s)
    db.session.commit()

@utils.traceback_enable
def delete_subnets(tenant_id, subnet_id):
    SapiProvisionedSubnets.query.filter_by(
            tenant_id = tenant_id,
            subnet_id = subnet_id).delete()
    db.session.commit()

@utils.traceback_enable
def update_subnets(tenant_id, subnet_id, subnet):
        SapiProvisionedSubnets.query.filter_by(
                tenant_id = tenant_id,
                subnet_id = subnet_id).update(subnet)
        db.session.commit()

#neutron port database representation
class SapiProvisionedPorts(db.Model):
    __tablename__ = "sapi_provisioned_ports"

    port_id = db.Column(db.String(UUID_LEN), primary_key = True)
    tenant_id = db.Column(db.String(UUID_LEN))
    network_id = db.Column(db.String(UUID_LEN))
    subnet_id = db.Column(db.String(UUID_LEN))
    device_id = db.Column(db.String(255))
    device_owner = db.Column(db.String(40))
    status = db.Column(db.String(40))
    admin_state_up = db.Column(db.Integer)
    binding_host_id = db.Column(db.String(40))
    mac_address = db.Column(db.String(255))
    ip_address = db.Column(db.String(255))

    def __init__(self, port_id, tenant_id, network_id,
            subnet_id, device_id, device_owner, status,
            admin_state_up, binding_host_id, mac_address, ip_address):
        self.port_id = port_id
        self.tenant_id = tenant_id
        self.network_id = network_id
        self.subnet_id = subnet_id
        self.device_id = device_id
        self.device_owner = device_owner
        self.status = status
        self.admin_state_up = admin_state_up
        self.binding_host_id = binding_host_id
        self.mac_address = mac_address
        self.ip_address = ip_address

    def sapi_port_representation(self):
        return {'port_id': self.port_id,
                'tenant_id': self.tenant_id,
                'network_id': self.network_id,
                'subnet_id': self.subnet_id,
                'device_id': self.device_id,
                'device_owner': self.device_owner,
                'status': self.status,
                'admin_state_up': self.admin_state_up,
                'binding_host_id': self.binding_host_id,
                'ip_address': self.ip_address,
                'mac_address': self.mac_address}

@utils.traceback_enable
def get_port(port_id):
    try:
        p = SapiProvisionedPorts.query.filter_by(
                port_id = port_id).one()
        return p.sapi_port_representation()
    except exc.NoResultFound:
        return None

@utils.traceback_enable
def delete_ports(tenant_id, port_id):
    SapiProvisionedPorts.query.filter_by(
            tenant_id = tenant_id,
            port_id = port_id).delete()
    db.session.commit()

@utils.traceback_enable
def persistence_ports(port):
    p = SapiProvisionedPorts(
            port_id = port['port_id'],
            tenant_id = port['tenant_id'],
            subnet_id = port['subnet_id'],
            network_id = port['network_id'],
            device_id = port['device_id'],
            device_owner = port['device_owner'],
            status = port['status'],
            admin_state_up = port['admin_state_up'],
            binding_host_id = port['binding_host_id'],
            ip_address = port['ip_address'],
            mac_address = port['mac_address'])
    db.session.add(p)
    db.session.commit()

@utils.traceback_enable
def update_ports(tenant_id, port_id, port):
    SapiProvisionedPorts.query.filter_by(
            tenant_id = tenant_id,
            port_id = port_id).update(port)
    db.session.commit()

#fake, only for test
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def __repr__(self):
        return '<User %r>' % self.username

    def sapi_user_representation(self):
        return {"username":self.username,
                "email":self.email}

class Agent(db.Model):
    __tablename__ = "agents"

    id = db.Column(db.String(UUID_LEN), primary_key = True)
    agent_type = db.Column(db.String(255))
    binary = db.Column(db.String(255))
    topic = db.Column(db.String(255))
    host = db.Column(db.String(255))
    admin_state_up = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    heartbeat_timestamp = db.Column(db.DateTime)
    description = db.Column(db.String(255))
    configurations = db.Column(db.String(255))

def persistence_user(user):
    u = User(email = user['email'],
             username = user['username'])
    try:
        db.session.add(u)
    except:
        pass
    finally:
        db.session.commit()

def get_user(username):
    try:
        u = User.query.filter_by(username=username).one()
    except:
        pass
    finally:
        return u.sapi_user_representation()

def delete_user(username):
    try:
        User.query.filter_by(username=username).delete()
    except:
        pass
    finally:
        db.session.commit()

def update_user(username, user):
    try:
        User.query.filter_by(username=username).update(user)
    except:
        pass
    finally:
        db.session.commit()

@utils.traceback_enable
def retrieve_nets():
    nets = SapiProvisionedNets.query.all()
    ret = dict((net.network_id, net.sapi_net_representation())
            for net in nets)
    return ret

@utils.traceback_enable
def retrieve_subnets():
    subnets = SapiProvisionedSubnets.query.all()
    ret = dict((subnet.subnet_id, subnet.sapi_subnet_representation())
            for subnet in subnets)
    return ret

@utils.traceback_enable
def retrieve_ports():
    ports = SapiProvisionedPorts.query.all()
    ret = dict((port.port_id, port.sapi_port_representation())
            for port in ports)
    return ret

def clear_database():
    nets = retrieve_nets()
    ports = retrieve_ports()
    subnets = retrieve_subnets()

    for id in nets:
        delete_nets(nets[id]['tenant_id'], id)
    for id in ports:
        delete_ports(ports[id]['tenant_id'], id)
    for id in subnets:
        delete_subnets(subnets[id]['tenant_id'], id)

def is_shared_net(network_id):
    try:
        net = SapiProvisionedNets.query.filter_by(
                network_id = network_id).one()
        return net.shared
    except exc.NoResultFound:
        return False

def retrieve_db_topology():
    all_ovs = Agent.query.all()
    return dict(
        (ovs.host, ovs.configurations)
        for ovs in all_ovs)
