#!/usr/bin/env python
# encoding: utf-8

import json
import traceback
from flask import Blueprint
from flask import jsonify
from flask import request, current_app

from sapi import utils
from sapi import app
from sapi.tor import h3c
from sapi.model import db_tor
from sapi.model import db_constants
from sapi.model import db_vlan_v2 as db_vlan
from sapi.model import db_neutron_v2 as db_neutron

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
                              db_constants.VLAN_SHARED - 2)
    topology[tor_ip]['vlanbitmap_shared'] = \
        utils.LocalVLanBitmap(db_constants.VLAN_SHARED,
                              db_constants.VLAN_MAX - 1)
    bitmap = topology[tor_ip]['vlanbitmap']
    shared_bitmap = topology[tor_ip]['vlanbitmap_shared']
    db_vlan_map = db_vlan.get_vlan_map(tor_ip)
    for id in db_vlan_map:
        allocated = db_vlan_map[id]['allocated']
        vlan_id = db_vlan_map[id]['vlan_id']
        if allocated:
            bitmap.add_bits(vlan_id)

    db_vlan_map_shared = db_vlan.get_vlan_map(tor_ip, shared=1)
    for id in db_vlan_map_shared:
        allocated = db_vlan_map_shared[id]['allocated']
        vlan_id = db_vlan_map_shared[id]['vlan_id']
        if allocated:
            shared_bitmap.add_bits(vlan_id)

#init database
def init_vlan_db(tor_ip):
    for vlan_id in range(
            db_constants.VLAN_MIN, db_constants.VLAN_SHARED - 1):
        db_vlan.add_vlan(tor_ip, vlan_id)
    for vlan_id in range(
            db_constants.VLAN_SHARED, db_constants.VLAN_MAX):
        db_vlan.add_vlan(tor_ip, vlan_id)

#before each request to /localvlan, update the topology
@vlan.before_request
@utils.traceback_enable
def get_topo():
    topo_db = db_neutron.retrieve_db_topology()
    topology = current_app._get_current_object().topology

    for host in topo_db:
        try:
            tunneling_ip = json.loads(topo_db[host])["tor_ip"]
        except KeyError:
            continue
        if tunneling_ip not in topology:
            topology[tunneling_ip] = {}
            topology[tunneling_ip]['hosts'] = []
        topology[tunneling_ip]['hosts'].append(host)
        if not db_vlan.is_tor_exists(tunneling_ip):
            init_vlan_db(tunneling_ip)

@vlan.route("/", methods = ['POST', 'GET'])
@vlan.route("/<string:portid>", methods = ['DELETE'])
@utils.traceback_enable
def topology(portid=None):
    topology = current_app._get_current_object().topology
    lock = current_app._get_current_object().lock
    conn = current_app._get_current_object().conn

    if request.method == 'GET':
        tor_ip = '10.216.24.102'
        _downlinks = db_tor.retrieve_tor_downlink(tor_ip)
        print parse_database_downlinks(_downlinks['if_index_range'])
        return "", 200

    if request.method == 'DELETE':
        with lock:
            pv_map = db_vlan.get_port_vlan_mapping(portid)
            if not pv_map:
                app.logger.warning('Port \'%s\' not in database port vlan mapping.' %(portid))
                return jsonify(message="port id not in port vlan map"), 404

            netid, tor_ip = pv_map['network_id'], pv_map['tor_ip']
            vlan_id = pv_map['vlan_id']
            db_vlan.delete_port_vlan_mapping(portid)
            nums = db_vlan.tor_port_vlan_entries(netid, tor_ip)
            shared = db_neutron.is_shared_net(netid)
            if nums == 0:
                if 'vlanbitmap' not in topology[tor_ip]:
                    init_vlan_bitmap(topology, tor_ip)
                if not shared:
                    topology[tor_ip]['vlanbitmap'].delete_bits(vlan_id)
                else:
                    topology[tor_ip]['vlanbitmap_shared'].delete_bits(vlan_id)
                db_vlan.unset_vlan_allocated(tor_ip, vlan_id)
                app.logger.warning('Reclaimed loval vlan \'%s\' for network \'%s\' on tor \'%s\'' %(
                    vlan_id, netid, tor_ip))

                #clear special configuration on interface
                app.logger.warning('Network \'%s\' vlan mapping is empty on TOR \'%s\', clear all configuration' %(
                    netid, tor_ip))
                ssh_conn = None
                try:
                    ssh_conn = conn[tor_ip]
                except:
                    app.logger.error('Tor connection failed, tor_ip = %s' %(tor_ip))
                    return 'Tor Connection failed.', 400
                if ssh_conn:
                    indexs, seg_id, tunnels, vlans = parse_tor(netid, tor_ip)
                    vsiname = 'vsi' + str(seg_id)
                    try:
                        unconfigure_all_downlinks(ssh_conn, indexs, vlans, vsiname, vlan_id)
                        delete_vsi_vxlan_with_tunnels(ssh_conn, vsiname, seg_id, tunnels)
                        db_tor.delete_vsi(tor_ip, vsiname)
                        app.logger.warning('Unconfig TOR Success: vsi=%s, segmentation_id=%s on tor_ip=%s, tor_index=%s, user data: netid=%s, portid=%s' %(
                                vsiname, seg_id, tor_ip, indexs, netid, portid))
                    except:
                        app.logger.error('Unconfig TOR Failed: vsi=%s, segmentation_id=%s on tor_ip=%s, tor_index=%s, user data: netid=%s, portid=%s' %(
                                vsiname, seg_id, tor_ip, indexs, netid, portid))
                        app.logger.error('Unconfig TOR Failed: %s', traceback.format_exc())
                        return 'Tor configuration failed.', 400
        return '', 200

    map = {}
    data = request.get_json()
    if not data or not validate(data):
        return jsonify(vlanmapping=map, message="Incorrect post data"), 400

    netid, host = data['netid'], data['host']
    portid = data['portid']
    tor_ip = select_tor_from_topo(topology, host)
    if not tor_ip:
        app.logger.warning('Host \'%s\' not in topology, POST data: tor \'%s\' network id \'%s\' port id \'%s\'' %(
            tor_ip, netid, portid))
        return jsonify(vlanmapping=map, message="Host not in topology"), 404

    if not db_neutron.get_network(netid):
        app.logger.warning('Network \'%s\' not founded, POST data: tor \'%s\' network id \'%s\' port id \'%s\'' %(
            tor_ip, netid, portid))
        return jsonify(vlanmapping=map, message="Network id not founded"), 404

    if not db_neutron.get_port(portid):
        app.logger.warning('Port \'%s\' not founded, POST data: tor \'%s\' network id \'%s\' port id \'%s\'' %(
            tor_ip, netid, portid))
        return jsonify(vlanmapping=map, message="Port id not founded"), 404

    with lock:
        if 'vlanbitmap' not in topology[tor_ip]:
            init_vlan_bitmap(topology, tor_ip)

        vlanbitmap = topology[tor_ip]['vlanbitmap']
        shared_vlanbitmap = topology[tor_ip]['vlanbitmap_shared']

        vm = db_vlan.get_vlan_allocation(netid, tor_ip)
        if vm:
            vlan_id = vm["vlan_id"]
        else:
            shared = db_neutron.is_shared_net(netid)
            vlan_id = shared_vlanbitmap.get_unused_bits() \
                    if shared else vlanbitmap.get_unused_bits()
            if not vlan_id:
                message = "vlan id out of range %d" %(db_constants.VLAN_MAX)
                return jsonify(vlanmapping=map, message=message), 400
            db_vlan.set_vlan_allocated(netid, tor_ip, vlan_id)
            app.logger.warning('Assigned loval vlan \'%s\' for network \'%s\' on TOR \'%s\'' %(
                vlan_id, netid, tor_ip))

            #configuration tor here
            # (1) get tor tunnels
            # (2) get tor vsi
            # (3) get tor downlink interface
            app.logger.warning('New network \'%s\' vlan mapping on TOR \'%s\', need to be configured.' %(
                netid, tor_ip))
            ssh_conn = None
            try:
                ssh_conn = conn[tor_ip]
            except:
                app.logger.error('Tor connection failed, tor_ip = %s' %(tor_ip))
                return 'Tor Connection failed.', 400

            if ssh_conn:
                indexs, seg_id, tunnels, vlans = parse_tor(netid, tor_ip)
                vsiname = 'vsi' + str(seg_id)
                try:
                    create_vsi_vxlan_with_tunnels(ssh_conn, vsiname, seg_id, tunnels)
                    configure_all_downlinks(ssh_conn, indexs, vlans, vsiname, vlan_id)
                    db_tor.save_vsi(tor_ip, vsiname)

                    app.logger.warning('Config TOR Success: vsi=%s, segmentation_id=%s on tor_ip=%s, tor_index=%s, POST data: host=%s, netid=%s, portid=%s' %(
                            vsiname, seg_id, tor_ip, indexs, host, netid, portid))
                except:
                    app.logger.error('Config TOR Failed: vsi=%s, segmentation_id=%s on tor_ip=%s, tor_index=%s, POST data: host=%s, netid=%s, portid=%s' %(
                            vsiname, seg_id, tor_ip, indexs, host, netid, portid))
                    app.logger.error('Config TOR Failed: %s', traceback.format_exc())
                    return 'Tor configuration failed.', 400

        if not db_vlan.is_exists_port_vlan(portid, tor_ip, vlan_id=vlan_id):
            db_vlan.add_port_vlan(portid, netid, tor_ip, vlan_id)

    map['vlan_id'] = vlan_id
    map['netid'] = netid
    map['host'] = host
    map['tor'] = tor_ip

    return jsonify(vlanmapping=map, message="OK"), 200

def parse_database_downlinks(index_string):
    downlinks = []
    try:
        if ';' not in index_string and '-' not in index_string:
            downlinks.append(int(index_string))
        items = index_string.split(';')
        for item in items:
            if '-' in item:
                _index = [int(index) for index in item.split('-')]
                for index in range(_index[0], _index[1] + 1):
                    downlinks.append(index)
            else:
                downlinks.append(int(item))
    except:
        pass
    return downlinks

#retrieve Network segmentation_id by netid, use tor_ip to retrieve
#tor downlinks, tor tunnels, and permit_vlans
#$downlinks: tor downlink, connect to host
#$tunnels: each vxlan tunnel between tors
#$permit_vlans: permit vlan ranges on all interfaces
def parse_tor(netid, tor_ip):
    _segmentation_id = db_neutron.get_network(netid)
    _downlinks = db_tor.retrieve_tor_downlink(tor_ip)
    _tunnels = db_tor.retrieve_tor_tunnels(tor_ip)
    _permit_vlans = db_vlan.get_tor_allocated_vlan(tor_ip)

    downlink_indexs = parse_database_downlinks(_downlinks['if_index_range'])
    segmentation_id = _segmentation_id['segmentation_id']
    tunnel_ids = [id for id in _tunnels]
    vlans = []
    for network_id in _permit_vlans:
        vlans.append(_permit_vlans[network_id]['vlan_id'])

    return list(set(downlink_indexs)), segmentation_id, tunnel_ids, vlans

#create vsi and vxlan, then config vxlan with tunnels
def create_vsi_vxlan_with_tunnels(ssh_conn, vsiname, vxlan_id, tunnels):
    vsi = h3c.VSI(ssh_conn, vsiname)
    vxlan = h3c.VXLAN(ssh_conn, vxlan_id)
    vxlan.vsi_name = vsiname
    vsi.create()
    vxlan.create()
    for tunnel_id in tunnels:
        vxlan.connect_vxlan_with_tunnel(tunnel_id)

#delete vsi and vxlan
def delete_vsi_vxlan_with_tunnels(ssh_conn, vsiname, vxlan_id, tunnels):
    vsi = h3c.VSI(ssh_conn, vsiname)
    vxlan = h3c.VXLAN(ssh_conn, vxlan_id)
    vxlan.vsi_name = vsiname
    vxlan.delete()
    vsi.delete()

#config all tor downlinks
def configure_all_downlinks(ssh_conn, indexs, vlans, vsiname, vlan_id):
    #permit_vlans = ','.join([str(vlan) for vlan in vlans])
    #permit_vlans += ',1'
    for index in indexs:
        interface = h3c.Interface(ssh_conn, index)
        #interface.port_trunk()
        #interface.port_trunk_permit_vlan(vlan_range=permit_vlans)
        interface.port_service_create(vlan_id, vlan_id)
        interface.port_ac_create(vlan_id, vsiname)

#unconfig all tor downlinks
def unconfigure_all_downlinks(ssh_conn, indexs, vlans, vsiname, vlan_id):
    #permit_vlans = ','.join([str(vlan) for vlan in vlans])
    #port_access = True if permit_vlans == '' else False
    #permit_vlans += ',1'
    for index in indexs:
        interface = h3c.Interface(ssh_conn, index)
        interface.port_ac_delete(vlan_id)
        interface.port_service_delete(vlan_id)
        #if port_access:
        #    interface.port_access()
        #else:
        #    interface.port_trunk_permit_vlan(vlan_range = permit_vlans)
