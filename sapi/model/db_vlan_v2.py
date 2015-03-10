#!/usr/bin/env python
# encoding: utf-8

from sqlalchemy.orm import exc

from sapi import db
from sapi import utils
from sapi.model import db_constants

UUID_LEN = db_constants.UUID_LEN
IP_ADDRESS = db_constants.IP_ADDRESS_LENGTH
UNUSED = db_constants.VLAN_UNSET
VLAN_MIN = db_constants.VLAN_MIN
VLAN_SHARED = db_constants.VLAN_SHARED
VLAN_MAX = db_constants.VLAN_MAX

class SapiVlanAllocations(db.Model):
    __tablename__ = "sapi_vlan_allocations"

    id = db.Column(db.INTEGER, primary_key = True)
    network_id = db.Column(db.String(UUID_LEN), default=UNUSED)
    tor_ip = db.Column(db.String(IP_ADDRESS))
    vlan_id = db.Column(db.INTEGER)
    allocated = db.Column(db.INTEGER)
    shared = db.Column(db.INTEGER)

    def __init__(self, network_id, tor_ip, vlan_id,
            allocated, shared):
        self.network_id = network_id
        self.tor_ip = tor_ip
        self.vlan_id = vlan_id
        self.allocated = allocated
        self.shared = shared

    def sapi_vlan_representation(self):
        return {'network_id': self.network_id,
                'tor_ip': self.tor_ip,
                'vlan_id': self.vlan_id,
                'allocated': self.allocated,
                'shared': self.shared}

class SapiPortVlanMapping(db.Model):
    __tablename__ = "sapi_port_vlan_mapping"

    port_id = db.Column(db.String(UUID_LEN), primary_key = True)
    network_id = db.Column(db.String(UUID_LEN))
    tor_ip = db.Column(db.String(IP_ADDRESS))
    vlan_id = db.Column(db.INTEGER)

    def __init__(self, port_id, network_id, tor_ip, vlan_id):
        self.port_id = port_id
        self.network_id = network_id
        self.tor_ip = tor_ip
        self.vlan_id = vlan_id

    def sapi_port_vlan_representation(self):
        return {'port_id': self.port_id,
                'network_id': self.network_id,
                'tor_ip': self.tor_ip,
                'vlan_id': self.vlan_id}

@utils.traceback_enable
def add_port_vlan(port_id, network_id, tor_ip, vlan_id):
    port_vlan_mapping = SapiPortVlanMapping(
            port_id = port_id,
            network_id = network_id,
            tor_ip = tor_ip,
            vlan_id = vlan_id)
    db.session.add(port_vlan_mapping)
    db.session.commit()

@utils.traceback_enable
def is_exists_port_vlan(port_id, tor_ip, vlan_id=None):
    if not vlan_id:
        nums = SapiPortVlanMapping.query.filter_by(
                port_id = port_id,
                tor_ip = tor_ip).count()
    else:
        nums = SapiPortVlanMapping.query.filter_by(
                port_id = port_id,
                tor_ip = tor_ip,
                vlan_id = vlan_id).count()
    return nums > 0

@utils.traceback_enable
def tor_port_vlan_entries(network_id, tor_ip):
    nums = SapiPortVlanMapping.query.filter_by(
            network_id = network_id,
            tor_ip = tor_ip).count()
    return nums

def get_port_vlan_mapping(port_id):
    try:
        p = SapiPortVlanMapping.query.filter_by(
                port_id = port_id).one()
        return p.sapi_port_vlan_representation()
    except exc.NoResultFound:
        return None

@utils.traceback_enable
def delete_port_vlan_mapping(port_id):
    SapiPortVlanMapping.query.filter_by(
            port_id = port_id).delete()
    db.session.commit()

@utils.traceback_enable
def add_vlan(tor_ip, vlan_id, allocated=0):
    v = SapiVlanAllocations(
            network_id = UNUSED,
            tor_ip = tor_ip,
            vlan_id = vlan_id,
            allocated = allocated,
            shared = 1 if vlan_id >= VLAN_SHARED else 0)
    db.session.add(v)
    db.session.commit()

@utils.traceback_enable
def set_vlan_allocated(network_id, tor_ip, vlan_id):
    SapiVlanAllocations.query.filter_by(
            tor_ip = tor_ip,
            vlan_id = vlan_id).update({'allocated':1,
                                       'network_id':network_id})
    db.session.commit()

@utils.traceback_enable
def unset_vlan_allocated(tor_ip, vlan_id):
    SapiVlanAllocations.query.filter_by(
            tor_ip = tor_ip,
            vlan_id = vlan_id).update({'allocated':0,
                                       'network_id':UNUSED})
    db.session.commit()

@utils.traceback_enable
def get_vlan_map(tor_ip, shared=0):
    vlans = SapiVlanAllocations.query.filter_by(
                tor_ip = tor_ip,
                shared = shared).all()

    res = dict((vlan.id, vlan.sapi_vlan_representation())
            for vlan in vlans)
    return res

@utils.traceback_enable
def is_tor_exists(tor_ip):
    num = SapiVlanAllocations.query.filter_by(
                tor_ip = tor_ip).count()
    if num > 0 and num < VLAN_MAX - VLAN_MIN - 1:
        return -1
    return num == (VLAN_MAX - VLAN_MIN - 1)

def get_vlan_allocation(network_id, tor_ip):
    try:
        vm = SapiVlanAllocations.query.filter_by(
                network_id = network_id,
                tor_ip = tor_ip,
                allocated = 1).one()
        return vm.sapi_vlan_representation()
    except exc.NoResultFound:
        return None

@utils.traceback_enable
def get_tor_allocated_vlan(tor_ip):
    allocated_vlans = SapiVlanAllocations.query.filter_by(
            tor_ip = tor_ip,
            allocated = 1).all()

    res = dict((av.network_id, av.sapi_vlan_representation())
            for av in allocated_vlans)
    return res
