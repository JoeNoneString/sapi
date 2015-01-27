#!/usr/bin/env python
# encoding: utf-8
import threading

from flask import Flask
from flask import request

from sapi.vlan import localvlan
from sapi.sdn import neutron
from sapi import utils

class SapiServer(Flask):
    def __init__(self, *args, **kwargs):
        super(SapiServer, self).__init__(*args, **kwargs)
        self.topology = {}
        self.lock = threading.Lock()

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
        return "HTTP Basic Auth required.", 403
    app.logger.warning("\'%s\' %s - %s <%s:%s>" %(
            request.method,
            request.url,
            request.remote_addr,
            auth.username,
            auth.password))
    if not auth or not utils.check_auth(auth):
        return utils.authenticate()
