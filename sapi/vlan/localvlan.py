#!/usr/bin/env python
# encoding: utf-8

import json
from flask import Blueprint
from flask import jsonify
from flask import request, current_app

from sapi.model import db_neutron
from sapi.model import db_vlan
from sapi.model import db_constants
from sapi import utils

vlan = Blueprint('vlan', __name__)

def validate(data):
    if 'netid' not in data or \
            'host' not in data or \
                'portid' not in data:
        return False
    return True

def select_tor_from_topo(topology, host):
    for tor_ip in topology:
        if host in topology[tor_ip]['hosts']:
            return tor_ip
    return None

def init_vlan_bitmap(topology, tor_ip):
    topology[tor_ip]['vlanbitmap'] = \
        utils.LocalVLanBitmap(db_constants.VLAN_MIN,
                              db_constants.VLAN_MAX)
    bitmap = topology[tor_ip]['vlanbitmap']
    db_vlan_map = db_vlan.get_vlan_map(tor_ip)
    for id in db_vlan_map:
        allocated = db_vlan_map[id]['allocated']
        vlan_id = db_vlan_map[id]['vlan_id']
        if allocated:
            bitmap.add_bits(vlan_id)

def init_vlan_db(netid, tor_ip):
    for vlan_id in range(
            db_constants.VLAN_MIN, db_constants.VLAN_MAX + 1):
        db_vlan.add_vlan(tor_ip, vlan_id)

@vlan.before_request
@utils.traceback_enable
def get_topo():
    topo_db = db_neutron.retrieve_db_topology()
    topology = current_app._get_current_object().topology

    for host in topo_db:
        tunneling_ip = json.loads(topo_db[host])["tunneling_ip"]
        if tunneling_ip not in topology:
            topology[tunneling_ip] = {}
        topology[tunneling_ip]['hosts'] = []
        topology[tunneling_ip]['hosts'].append(host)

@vlan.route("/", methods = ['POST'])
@vlan.route("/<string:portid>", methods = ['DELETE'])
@utils.traceback_enable
def topology(portid=None):
    topology = current_app._get_current_object().topology
    lock = current_app._get_current_object().lock

    if request.method == 'DELETE':
        with lock:
            pv_map = db_vlan.get_port_vlan_mapping(portid)
            if not pv_map:
                return jsonify(message="port id not in port vlan map"), 404
            netid, tor_ip = pv_map['network_id'], pv_map['tor_ip']
            vlan_id = pv_map['vlan_id']
            db_vlan.delete_port_vlan_mapping(portid)
            nums = db_vlan.tor_port_vlan_entries(netid, tor_ip)
            if nums == 0:
                topology[tor_ip]['vlanbitmap'].delete_bits(vlan_id)
                db_vlan.unset_vlan_allocated(tor_ip, vlan_id)
        return '', 200

    map = {}
    data = request.get_json()
    if not data or not validate(data):
        return jsonify(vlanmapping=map, message="Incorrect post data"), 400

    netid, host = data['netid'], data['host']
    portid = data['portid']
    tor_ip = select_tor_from_topo(topology, host)
    if not tor_ip:
        return jsonify(vlanmapping=map, message="Host not in topology"), 404

    if not db_vlan.is_tor_exists(tor_ip):
        init_vlan_db(netid, tor_ip)

    #if 'vlanmap' not in topology[tor_ip]:
    #    topology[tor_ip]['vlanmap'] = {}

    with lock:
        if 'vlanbitmap' not in topology[tor_ip]:
            init_vlan_bitmap(topology, tor_ip)

        #torvlanmap = topology[tor_ip]['vlanmap']
        vlanbitmap = topology[tor_ip]['vlanbitmap']

        vm = db_vlan.get_vlan_allocation(netid, tor_ip)
        if vm:
            vlan_id = vm["vlan_id"]
        else:
            vlan_id = vlanbitmap.get_unused_bits()
            if not vlan_id:
                message = "vlan id out of range %d" %(db_constants.VLAN_MAX)
                return jsonify(vlanmapping=map, message=message), 400
            db_vlan.set_vlan_allocated(netid, tor_ip, vlan_id)

        if not db_vlan.is_exists_port_vlan(portid, tor_ip, vlan_id=vlan_id):
            db_vlan.add_port_vlan(portid, netid, tor_ip, vlan_id)

    map['vlan_id'] = vlan_id
    map['netid'] = netid
    map['host'] = host
    map['tor'] = tor_ip

    return jsonify(vlanmapping=map, message="OK"), 200
