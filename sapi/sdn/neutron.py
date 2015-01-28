#!/usr/bin/env python
# encoding: utf-8
import traceback

from flask import request
from flask import jsonify
from flask.views import MethodView
from sapi.model import db_neutron
from sapi import utils

class HttpStatusCode(object):
    RESOURCE_KEY=""
    def __init__(self):
        self._status = {
            400: "bad request, maybe arguments error",
            404: "%s not found" %(self.RESOURCE_KEY),
            200: "ok"}

    def return_jsonify(self, code):
        return jsonify(message=self._status[code]), code

class NetworkBase(object):
    def _check_if_older_net(self, net):
        older_net = db_neutron.is_older_nets(net['tenant_id'],
                                             net['provider:segmentation_id'],
                                             net['provider:network_type'])
        if older_net:
            db_neutron.delete_nets(older_net['tenant_id'],
                                   older_net['network_id'])

    @utils.traceback_enable
    def _make_db_net_dict(self, net):
        try:
            network_id = net['id']
            tenant_id = net['tenant_id']
            segmentation_id = net['provider:segmentation_id']
            segmentation_type = net['provider:network_type']
            admin_state_up = 1 if net['admin_state_up'] else 0
            shared = 1 if net['shared'] else 0
        except KeyError:
            raise ValueError("Received wrong Ml2 driver network data")

        return {'network_id': network_id,
                'tenant_id': tenant_id,
                'segmentation_id': segmentation_id,
                'segmentation_type': segmentation_type,
                'admin_state_up': admin_state_up,
                'shared': shared}

class PortBase(object):
    @utils.traceback_enable
    def _make_db_port_dict(self, port):
        subnet_id = ''
        ip_address = ''
        binding_host_id = ''

        try:
            binding_host_id = port['binding:host_id']
        except KeyError:
            pass

        try:
            if len(port['fixed_ips']) > 0:
                subnet_id = port['fixed_ips'][0]['subnet_id']
                ip_address = port['fixed_ips'][0]['ip_address']
        except:
            pass

        return {'port_id': port['id'],
                'tenant_id': port['tenant_id'],
                'network_id': port['network_id'],
                'subnet_id': subnet_id,
                'device_id': port['device_id'],
                'device_owner': port['device_owner'],
                'status': port['status'],
                'admin_state_up': 1 if port['admin_state_up'] else 0,
                'binding_host_id': binding_host_id,
                'ip_address': ip_address,
                'mac_address': port['mac_address']}

class SubnetBase(object):
    @utils.traceback_enable
    def _make_db_subnet_dict(self, subnet):
        try:
            subnet_id = subnet['id']
            network_id = subnet['network_id']
            tenant_id = subnet['tenant_id']
            shared = 1 if subnet['shared'] else 0
            enable_dhcp = 1 if subnet['enable_dhcp'] else 0
        except KeyError:
            raise ValueError("Received wrong Ml2 driver subnet data")

        return {'subnet_id': subnet_id,
                'network_id': network_id,
                'tenant_id': tenant_id,
                'shared': shared,
                'enable_dhcp': enable_dhcp}

class SyncApi(MethodView, HttpStatusCode,
              NetworkBase, PortBase, SubnetBase):
    def post(self):
        try:
            sync_info = request.get_json()['sina_openstack']

            #Sync info from the ml2 driver, always clear the database.
            db_neutron.clear_database()

            self._sync_network(sync_info['network'])
            self._sync_subnet(sync_info['subnet'])
            self._sync_port(sync_info['port'])
        except:
            return self.return_jsonify(400)
        return self.return_jsonify(200)

    def _sync_network(self, nets):
        for _net in nets:
            db_neutron.persistence_nets(
                    self._make_db_net_dict(_net))

    def _sync_subnet(self, subnets):
        for _subnet in subnets:
            db_neutron.persistence_subnets(
                    self._make_db_subnet_dict(_subnet))

    def _sync_port(self, ports):
        for _port in ports:
            db_neutron.persistence_ports(
                    self._make_db_port_dict(_port))

class NetApi(MethodView, HttpStatusCode, NetworkBase):
    RESOURCE_KEY="network id"

    def get(self, net_id):
        if not net_id:
            return self.return_jsonify(400)

        net = db_neutron.get_network(net_id)
        if not net:
            return self.return_jsonify(404)
        return jsonify(network=net)

    def post(self):
        try:
            network = request.get_json()['network']
        except KeyError:
            return self.return_jsonify(400)

        self._persistence_nets(self._make_db_net_dict(network))
        return self.return_jsonify(200)

    def put(self, net_id):
        net = db_neutron.get_network(net_id)
        if not net:
            return self.return_jsonify(404)

        try:
            network = request.get_json()['network']
        except KeyError:
            return self.return_jsonify(400)

        self._update_nets(self._make_db_net_dict(network))
        return self.return_jsonify(200)

    def delete(self, net_id):
        net = db_neutron.get_network(net_id)
        if not net:
            return self.return_jsonify(404)

        self._delete_nets(net['tenant_id'],
                          net['network_id'])
        return self.return_jsonify(200)

    @utils.traceback_enable
    def _persistence_nets(self, network):
        db_neutron.persistence_nets(network)

    @utils.traceback_enable
    def _delete_nets(self, tenant_id, network_id):
        db_neutron.delete_nets(tenant_id, network_id)

    @utils.traceback_enable
    def _update_nets(self, network):
        db_neutron.update_nets(network['tenant_id'],
                               network['network_id'],
                               network)

class SubnetApi(MethodView, HttpStatusCode, SubnetBase):
    RESOURCE_KEY = "subnet id"

    def get(self, subnet_id):
        if not subnet_id:
            return self.return_jsonify(404)

        subnet = self._get_subnet(subnet_id)
        if not subnet:
            return self.return_jsonify(404)

        return jsonify(subnet=subnet)

    def post(self):
        try:
            subnet = request.get_json()['subnet']
        except KeyError:
            return self.return_jsonify(400)

        self._persistence_subnets(self._make_db_subnet_dict(subnet))

        return self.return_jsonify(200)

    def put(self, subnet_id):
        subnet = db_neutron.get_subnet(subnet_id)
        if not subnet:
            return self.return_jsonify(404)

        try:
            subnet = request.get_json()['subnet']
        except KeyError:
            return self.return_jsonify(400)

        self._update_subnets(self._make_db_subnet_dict(subnet))

        return self.return_jsonify(200)

    def delete(self, subnet_id):
        subnet = db_neutron.get_subnet(subnet_id)
        if not subnet:
            return self.return_jsonify(404)

        self._delete_subnets(subnet)

        return self.return_jsonify(200)

    @utils.traceback_enable
    def _get_subnet(self, subnet_id):
        return db_neutron.get_subnet(subnet_id)

    @utils.traceback_enable
    def _persistence_subnets(self, subnet):
        db_neutron.persistence_subnets(subnet)

    @utils.traceback_enable
    def _delete_subnets(self, subnet):
        db_neutron.delete_subnets(subnet['tenant_id'], subnet['subnet_id'])

    @utils.traceback_enable
    def _update_subnets(self, subnet):
        db_neutron.update_subnets(subnet['tenant_id'],
                                  subnet['subnet_id'],
                                  subnet)

class PortApi(MethodView, HttpStatusCode, PortBase):
    RESOURCE_KEY = "port id"

    def get(self, port_id):
        if not port_id:
            return self.return_jsonify(404)

        port = self._get_port(port_id)
        if not port:
            return self.return_jsonify(404)

        return jsonify(port=port)

    def post(self):
        try:
            _port = request.get_json()['port']
        except KeyError:
            return self.return_jsonify(400)

        port = self._make_db_port_dict(_port)
        self._persistence_port(port)

        return self.return_jsonify(200)

    def put(self, port_id):
        port = db_neutron.get_port(port_id)
        if not port:
            return self.return_jsonify(404)

        try:
            _port = request.get_json()['port']
        except KeyError:
            return self.return_jsonify(400)

        port = self._make_db_port_dict(_port)
        self._update_port(port)

        return self.return_jsonify(200)

    def delete(self, port_id):
        port = db_neutron.get_port(port_id)
        if not port:
            return self.return_jsonify(404)

        self._delete_port(port['tenant_id'], port['port_id'])

        return self.return_jsonify(200)

    @utils.traceback_enable
    def _get_port(self, port_id):
        return db_neutron.get_port(port_id)

    @utils.traceback_enable
    def _update_port(self, port):
        db_neutron.update_ports(port['tenant_id'],
                                port['port_id'],
                                port)

    @utils.traceback_enable
    def _persistence_port(self, port):
        db_neutron.persistence_ports(port)

    @utils.traceback_enable
    def _delete_port(self, tenant_id, port_id):
        db_neutron.delete_ports(tenant_id, port_id)
