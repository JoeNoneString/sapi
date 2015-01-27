#!/usr/bin/env python
# encoding: utf-8

import sqlalchemy as sa
from sqlalchemy.orm import exc
import traceback

import neutron.db.api as db
from neutron.db import model_base
from neutron.db import models_v2
from oslo.config import cfg
from sapi.model import db_constants

CONF = cfg.CONF
UUID_LEN = db_constants.UUID_LEN
IP_ADDRESS = db_constants.IP_ADDRESS_LENGTH
UNUSED = db_constants.VLAN_UNSET

class SapiVlanAllocations(model_base.BASEV2, models_v2.HasId):
    __tablename__ = "sapi_vlan_allocations"

    network_id = sa.Column(sa.String(UUID_LEN), default=UNUSED)
    tor_ip = sa.Column(sa.String(IP_ADDRESS))
    vlan_id = sa.Column(sa.INTEGER)
    allocated = sa.Column(sa.INTEGER)

    def sapi_vlan_representation(self):
        return {'network_id': self.network_id,
                'tor_ip': self.tor_ip,
                'vlan_id': self.vlan_id,
                'allocated': self.allocated}

class SapiPortVlanMapping(model_base.BASEV2):
    __tablename__ = "sapi_port_vlan_mapping"

    port_id = sa.Column(sa.String(UUID_LEN), primary_key = True)
    network_id = sa.Column(sa.String(UUID_LEN))
    tor_ip = sa.Column(sa.String(IP_ADDRESS))
    vlan_id = sa.Column(sa.INTEGER)

    def sapi_port_vlan_representation(self):
        return {'port_id': self.port_id,
                'network_id': self.network_id,
                'tor_ip': self.tor_ip,
                'vlan_id': self.vlan_id}

def add_port_vlan(port_id, network_id, tor_ip, vlan_id):
    session = db.get_session()
    with session.begin():
        port_vlan_mapping = SapiPortVlanMapping(
                    port_id = port_id,
                    network_id = network_id,
                    tor_ip = tor_ip,
                    vlan_id = vlan_id)
        session.add(port_vlan_mapping)

def is_exists_port_vlan(port_id, tor_ip, vlan_id=None):
    session = db.get_session()
    with session.begin():
        if not vlan_id:
            nums = (session.query(SapiPortVlanMapping).
                    filter_by(port_id = port_id,
                              tor_ip = tor_ip).count())
        else:
            nums = (session.query(SapiPortVlanMapping).
                    filter_by(port_id = port_id,
                              tor_ip = tor_ip,
                              vlan_id = vlan_id).count())
        return nums > 0

def tor_port_vlan_entries(network_id, tor_ip):
    session = db.get_session()
    with session.begin():
        nums = (session.query(SapiPortVlanMapping).
                filter_by(network_id = network_id,
                          tor_ip = tor_ip).count())
        return nums

def get_port_vlan_mapping(port_id):
    session = db.get_session()
    with session.begin():
        try:
            model = SapiPortVlanMapping
            port_vlan_mapping = (session.query(model).
                                 filter(model.port_id == port_id).one())
        except exc.NoResultFound:
            return None
        return port_vlan_mapping.sapi_port_vlan_representation()

def delete_port_vlan_mapping(port_id):
    session = db.get_session()
    with session.begin():
        (session.query(SapiPortVlanMapping).
         filter_by(port_id = port_id).delete())

def add_vlan(tor_ip, vlan_id, allocated=0):
    session = db.get_session()
    with session.begin():
        vlan = SapiVlanAllocations(
                tor_ip = tor_ip,
                vlan_id = vlan_id,
                allocated = allocated)
        session.add(vlan)

def set_vlan_allocated(network_id, tor_ip, vlan_id):
    session = db.get_session()
    with session.begin():
        (session.query(SapiVlanAllocations).
         filter_by(tor_ip = tor_ip,
                   vlan_id = vlan_id).update({'allocated':1,
                                              'network_id': network_id}))

def unset_vlan_allocated(tor_ip, vlan_id):
    session = db.get_session()
    with session.begin():
        (session.query(SapiVlanAllocations).
         filter_by(tor_ip = tor_ip,
                   vlan_id = vlan_id).update({'allocated':0,
                                              'network_id':UNUSED}))

def get_vlan_map(tor_ip):
    session = db.get_session()
    with session.begin():
        model = SapiVlanAllocations
        vlans = (session.query(model).
                   filter(model.tor_ip == tor_ip))

        res = dict((vlan.id, vlan.sapi_vlan_representation())
                for vlan in vlans)

        return res

def is_tor_exists(tor_ip):
    session = db.get_session()
    with session.begin():
        num = (session.query(SapiVlanAllocations).
               filter_by(tor_ip = tor_ip).count())

        return num > 0

def get_vlan_allocation(network_id, tor_ip):
    session = db.get_session()
    with session.begin():
        model = SapiVlanAllocations
        try:
            vm = (session.query(model).
                  filter(model.network_id == network_id,
                         model.tor_ip == tor_ip,
                         model.allocated == 1).one())
        except exc.NoResultFound:
            return None
        return vm.sapi_vlan_representation()
