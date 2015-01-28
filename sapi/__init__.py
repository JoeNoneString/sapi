#!/usr/bin/env python
# encoding: utf-8
import threading
import json
import time

from flask import Flask
from flask import request

from sapi import utils
from sapi.vlan import localvlan
from sapi.sdn import neutron
from sapi.model import db_neutron
from sapi.model import db_vlan
from sapi.model import db_constants


class SapiServer(Flask):
    def __init__(self, *args, **kwargs):
        super(SapiServer, self).__init__(*args, **kwargs)
        self.topology = self.get_topo()
        self.lock = threading.Lock()

    def init_vlan_db(self, tor_ip):
        for vlan_id in range(
                db_constants.VLAN_MIN, db_constants.VLAN_MAX):
            db_vlan.add_vlan(tor_ip, vlan_id)

    def get_topo(self):
        topo_db = db_neutron.retrieve_db_topology()
        topology = {}

        now = time.time()
        print " * Init Tor vlan map in database, plz wait for a while..."
        for host in topo_db:
            try:
                tunneling_ip = json.loads(topo_db[host])["tor_ip"]
            except KeyError:
                continue

            if tunneling_ip not in topology:
                topology[tunneling_ip] = {}
            topology[tunneling_ip]['hosts'] = []
            topology[tunneling_ip]['hosts'].append(host)

            db_status = db_vlan.is_tor_exists(tunneling_ip)
            if db_status == -1:
                raise ValueError("database in wrong state, plz manually clear it.")

            if not db_vlan.is_tor_exists(tunneling_ip):
                self.init_vlan_db(tunneling_ip)
        latest = time.time()
        print " * Init database success, time: %s" %(latest - now)

        return topology

app = SapiServer(__name__)

utils.init_logger(app)
app.config.from_object('config.default_settings.ProductionConfig')

app.register_blueprint(localvlan.vlan, url_prefix='/localvlan')
utils.register_api(app, neutron.NetApi,    'net_api',    '/network/',pk='net_id',   pk_type="string")
utils.register_api(app, neutron.SubnetApi, 'subnet_api', '/subnet/', pk='subnet_id',pk_type="string")
utils.register_api(app, neutron.PortApi,   'port_api',   '/port/',   pk='port_id',  pk_type="string")
utils.register_api(app, neutron.SyncApi,   'sync_api',   '/sync/')

@app.before_request
def auth_required():
    auth = request.authorization
    if not auth:
        return "HTTP Basic Auth required.", 401
    app.logger.warning("\'%s\' %s - %s <%s:%s>" %(
            request.method,
            request.url,
            request.remote_addr,
            auth.username,
            auth.password))
    if not auth or not utils.check_auth(auth):
        return utils.authenticate()
