#!/usr/bin/env python
# encoding: utf-8

import sqlalchemy as sa
from sqlalchemy.orm import exc

import neutron.db.api as db
from neutron.db import model_base
from neutron.db import models_v2
from oslo.config import cfg
from neutron.db import agents_db
from sapi.model import db_exception
from sapi.model import db_constants

CONF = cfg.CONF
UUID_LEN = db_constants.UUID_LEN
OVS_TYPE = db_constants.OVS_TYPE

class SapiProvisionedNets(model_base.BASEV2, models_v2.HasId,
                          models_v2.HasTenant):
    __tablename__ = "sapi_provisioned_nets"

    network_id = sa.Column(sa.String(UUID_LEN))
    segmentation_id = sa.Column(sa.Integer)
    segmentation_type = sa.Column(sa.String(UUID_LEN))
    admin_status_up = sa.Column(sa.Integer)

    def sapi_net_representation(self):
        return {'network_id': self.network_id,
                'segmentation_id': self.segmentation_id,
                'segmentation_type': self.segmentation_type,
                'admin_status_up': self.admin_status_up,
                'tenant_id': self.tenant_id}

class SapiProvisionedSubnets(model_base.BASEV2, models_v2.HasTenant):
    __tablename__ = "sapi_provisioned_subnets"

    enable_dhcp = sa.Column(sa.Integer)
    subnet_id = sa.Column(sa.String(UUID_LEN), primary_key=True)
    network_id = sa.Column(sa.String(UUID_LEN))
    shared = sa.Column(sa.Integer)

    def sapi_subnet_representation(self):
        return {'subnet_id': self.subnet_id,
                'network_id': self.network_id,
                'tenant_id': self.tenant_id,
                'shared': self.shared,
                'enable_dhcp': self.enable_dhcp}

class SapiProvisionedPorts(model_base.BASEV2, models_v2.HasTenant):
    __tablename__ = "sapi_provisioned_ports"

    port_id = sa.Column(sa.String(UUID_LEN), primary_key = True)
    network_id = sa.Column(sa.String(UUID_LEN))
    subnet_id = sa.Column(sa.String(UUID_LEN))
    device_id = sa.Column(sa.String(255))
    device_owner = sa.Column(sa.String(40))
    status = sa.Column(sa.String(40))
    admin_state_up = sa.Column(sa.Integer)
    binding_host_id = sa.Column(sa.String(40))
    mac_address = sa.Column(sa.String(255))
    ip_address = sa.Column(sa.String(255))

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

def persistence_ports(port):
    session = db.get_session()
    with session.begin():
        port = SapiProvisionedPorts(
                port_id = port['port_id'],
                tenant_id = port['tenant_id'],
                network_id = port['network_id'],
                subnet_id = port['subnet_id'],
                device_id = port['device_id'],
                device_owner = port['device_owner'],
                status = port['status'],
                admin_state_up = port['admin_state_up'],
                binding_host_id = port['binding_host_id'],
                ip_address = port['ip_address'],
                mac_address = port['mac_address'])
        session.add(port)

def persistence_nets(tenant_id, network_id,
                     segmentation_id, segmentation_type,
                     admin_status_up=1):
    session = db.get_session()
    with session.begin():
        net = SapiProvisionedNets(
                tenant_id = tenant_id,
                network_id = network_id,
                segmentation_id = segmentation_id,
                segmentation_type = segmentation_type,
                admin_status_up = admin_status_up)
        session.add(net)

def persistence_subnets(subnet_id, network_id,
                        tenant_id, shared, enable_dhcp):
    session = db.get_session()
    with session.begin():
        subnet = SapiProvisionedSubnets(
                tenant_id = tenant_id,
                network_id = network_id,
                subnet_id = subnet_id,
                enable_dhcp = enable_dhcp,
                shared = shared)
        session.add(subnet)

def retrieve_subnets():
    session = db.get_session()
    with session.begin():
        model = SapiProvisionedSubnets
        all_subnets = (session.query(model))
        res = dict(
            (subnet.subnet_id, subnet.sapi_subnet_representation())
            for subnet in all_subnets)
        return res

def retrieve_ports():
    session = db.get_session()
    with session.begin():
        model = SapiProvisionedPorts
        all_ports = (session.query(model))
        res = dict(
            (port.port_id, port.sapi_port_representation())
            for port in all_ports)
        return res

def retrieve_nets():
    session = db.get_session()
    with session.begin():
        model = SapiProvisionedNets
        all_nets = (session.query(model))
        res = dict(
            (net.network_id, net.sapi_net_representation())
            for net in all_nets)
        return res

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


def get_subnet(subnet_id):
    session = db.get_session()
    with session.begin():
        try:
            subnet = (session.query(SapiProvisionedSubnets).
                      filter_by(subnet_id = subnet_id).one())
        except exc.NoResultFound:
            return None
        return subnet.sapi_subnet_representation()

def get_network(network_id):
    session = db.get_session()
    with session.begin():
        try:
            net = (session.query(SapiProvisionedNets).
                   filter_by(network_id = network_id).one())
        except exc.NoResultFound:
            return None
        return net.sapi_net_representation()

def get_port(port_id):
    session = db.get_session()
    with session.begin():
        try:
            port = (session.query(SapiProvisionedPorts).
                    filter_by(port_id = port_id).one())
        except exc.NoResultFound:
            return None
        return port.sapi_port_representation()

def delete_subnets(tenant_id, subnet_id):
    session = db.get_session()
    with session.begin():
        (session.query(SapiProvisionedSubnets).
         filter_by(tenant_id=tenant_id, subnet_id=subnet_id).
         delete())

def delete_nets(tenant_id, network_id):
    session = db.get_session()
    with session.begin():
        (session.query(SapiProvisionedNets).
         filter_by(tenant_id=tenant_id, network_id=network_id).
         delete())

def delete_ports(tenant_id, port_id):
    session = db.get_session()
    with session.begin():
        (session.query(SapiProvisionedPorts).
         filter_by(tenant_id=tenant_id, port_id=port_id).
         delete())

def update_subnets(tenant_id, subnet_id, shared, enable_dhcp):
    session = db.get_session()
    with session.begin():
        try:
            (session.query(SapiProvisionedSubnets).
             filter_by(tenant_id = tenant_id,
                       subnet_id = subnet_id).
                            update({'shared': shared,
                                    'enable_dhcp': enable_dhcp}))
        except exc.NoResultFound:
            raise db_exception.DBnotfounded()
        except exc.MultipleResultsFound:
            raise db_exception.Multipledbfounded()

def update_nets(tenant_id, network_id, admin_state_up):
    session = db.get_session()
    with session.begin():
        try:
            (session.query(SapiProvisionedNets).
             filter_by(tenant_id = tenant_id,
                       network_id = network_id).
                            update({'admin_status_up':admin_state_up}))
        except exc.NoResultFound:
            raise db_exception.DBnotfounded()
        except exc.MultipleResultsFound:
            raise db_exception.Multipledbfounded()

def update_ports(tenant_id, port_id, port):
    session = db.get_session()
    with session.begin():
        try:
            (session.query(SapiProvisionedPorts).
             filter_by(tenant_id = tenant_id,
                       port_id = port_id).
                            update(port))
        except exc.NoResultFound:
            raise db_exception.DBnotfounded()
        except exc.MultipleResultsFound:
            raise db_exception.Multipledbfounded()

def is_provisioned_nets(tenant_id, network_id, segmentation_id=None):
    session = db.get_session()
    with session.begin():
        if not segmentation_id:
            num_nets = (session.query(SapiProvisionedNets).
                        filter_by(tenant_id = tenant_id,
                                  network_id = network_id).count())
        else:
            num_nets = (session.query(SapiProvisionedNets).
                        filter_by(tenant_id = tenant_id,
                                  network_id = network_id,
                                  segmentation_id = segmentation_id).count())
    return num_nets > 0

def is_provisioned_subnets(tenant_id, subnet_id):
    session = db.get_session()
    with session.begin():
        subnets = (session.query(SapiProvisionedSubnets).
                  filter_by(tenant_id = tenant_id,
                            subnet_id = subnet_id).count())
    return subnets > 0

def is_provisioned_ports(tenant_id, port_id):
    session = db.get_session()
    with session.begin():
        ports = (session.query(SapiProvisionedPorts).
                  filter_by(tenant_id = tenant_id,
                            port_id = port_id).count())
    return ports > 0

def is_older_nets(tenant_id, segmentation_id, segmentation_type):
    session = db.get_session()
    with session.begin():
        try:
            net = (session.query(SapiProvisionedNets).
                   filter_by(tenant_id = tenant_id,
                             segmentation_id = segmentation_id,
                             segmentation_type = segmentation_type).one())
        except:
            return None
    return net.sapi_net_representation()

def retrieve_db_topology():
    session = db.get_session()
    with session.begin():
        model = agents_db.Agent
        all_ovs = (session.query(model).
                   filter(model.agent_type == OVS_TYPE,
                          model.admin_state_up == 1))
        return dict(
            (ovs.host, ovs.configurations)
            for ovs in all_ovs)
