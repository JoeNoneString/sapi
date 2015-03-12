#!/usr/bin/env python
# encoding: utf-8
import json
import atexit
import time
import threading
from flask import Flask, render_template
from flask import request
from flask.ext.sqlalchemy import SQLAlchemy

class SapiServer(Flask):
    def __init__(self, *args, **kwargs):
        super(SapiServer, self).__init__(*args, **kwargs)
        self.topology = {}
        self.lock = threading.Lock()
        self.conn = {}
        self.time = time.time()
app = SapiServer(__name__)
app.config.from_object('config.default_settings.ProductionConfig')
db = SQLAlchemy(app)

from sapi import utils
utils.init_logger(app)

from sapi.tor import tor
from sapi.sdn import neutron
from sapi.vlan import localvlan
from sapi.tor import tor_register
from sapi.model import db_constants
from sapi.model import db_vlan_v2 as db_vlan
from sapi.model import db_neutron_v2 as db_neutron

def init_vlan_db(tor_ip):
    for vlan_id in range(
            db_constants.VLAN_MIN, db_constants.VLAN_SHARED - 1):
        db_vlan.add_vlan(tor_ip, vlan_id)
    for vlan_id in range(
            db_constants.VLAN_SHARED, db_constants.VLAN_MAX):
        db_vlan.add_vlan(tor_ip, vlan_id)

def get_topo():
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
        if host not in topology[tunneling_ip]['hosts']:
            topology[tunneling_ip]['hosts'].append(host)

        db_status = db_vlan.is_tor_exists(tunneling_ip)
        if db_status == -1:
            raise ValueError("database in wrong state, plz manually clear it.")
        if not db_status:
            init_vlan_db(tunneling_ip)

    latest = time.time()
    print " * Init database success, time: %s" %(latest - now)
    return topology

@atexit.register
def destory():
    for conn in app.conn:
        try:
            with app.conn[conn] as m:
                m.close_session()
        except:
            pass

app.topology = get_topo()
app.register_blueprint(localvlan.vlan, url_prefix='/localvlan')
app.register_blueprint(tor_register.register, url_prefix='/tor')
utils.register_api(app, neutron.NetApi,    'net_api',    '/network/',pk='net_id',   pk_type="string")
utils.register_api(app, neutron.SubnetApi, 'subnet_api', '/subnet/', pk='subnet_id',pk_type="string")
utils.register_api(app, neutron.PortApi,   'port_api',   '/port/',   pk='port_id',  pk_type="string")
utils.register_api(app, neutron.SyncApi,   'sync_api',   '/sync/')

@app.before_request
def auth_required():
    now = time.time()
    expire = now - app.time
    app.time = now
    if expire > app.config['SSH_TIMEOUT'] or app.conn == {}:
        for tor_ip in app.topology:
            try:
                app.conn[tor_ip] = tor.ConnTor(
                            tor_ip,
                            app.config['USERNAME'],
                            app.config['PASSWORD'])
            except:
                app.logger.critical("Tor Connection Error, IP: %s" %(tor_ip))
    auth = request.authorization
    #if not auth:
    #    return "HTTP Basic Auth required.", 401
    if not auth or not utils.check_auth(auth):
        return utils.authenticate()
    app.logger.warning("%-6s %s from %s" %(
            request.method,
            request.url,
            request.remote_addr))

#from sapi.tor import h3c
#
#@app.route('/register', methods=['GET', 'POST'])
#def register_tor():
#    if request.method == 'POST':
#        print request.form['torIp'], request.form['srcIp']
#        return render_template('boot.html')
#    return render_template('tor.html')
