#!/usr/bin/env python
# encoding: utf-8
from sqlalchemy.orm import exc

from sapi import db
from sapi import utils
from sapi.model import db_constants

class SapiTorDownlink(db.Model):
    __tablename__ = "sapi_tor_downlink"

    tor_ip = db.Column(db.String(db_constants.IP_ADDRESS_LENGTH), primary_key = True)
    if_index_range = db.Column(db.String(255))

    def __init__(self, tor_ip, if_index_range):
        self.tor_ip = tor_ip
        self.if_index_range = if_index_range

    def sapi_tor_representation(self):
        return {'tor_ip':self.tor_ip,
                'if_index_range':self.if_index_range}

@utils.traceback_enable
def retrieve_tor_downlink(tor_ip):
    td = SapiTorDownlink.query.filter_by(
            tor_ip = tor_ip).one()
    return td.sapi_tor_representation()

@utils.traceback_enable
def save_tor_downlink(tor_ip, downlinks):
    td = SapiTorDownlink(tor_ip = tor_ip,
            if_index_range = downlinks)
    db.session.add(td)
    db.session.commit()

@utils.traceback_enable
def delete_tor_downlink(tor_ip):
    SapiTorDownlink.query.filter_by(
            tor_ip = tor_ip).delete()
    db.session.commit()

class SapiTorVsis(db.Model):
    __tablename__ = 'sapi_tor_vsis'

    id = db.Column(db.INTEGER, primary_key = True, autoincrement=True)
    tor_ip = db.Column(db.String(db_constants.IP_ADDRESS_LENGTH))
    vsi_name = db.Column(db.String(45))

    def __init__(self, tor_ip, vsi_name):
        self.tor_ip = tor_ip
        self.vsi_name = vsi_name

    def sapi_tor_vsi_representation(self):
        return {'tor_ip': self.tor_ip,
                'vsi_name': self.vsi_name}

@utils.traceback_enable
def retrieve_vsis(tor_ip):
    tt = SapiTorVsis.query.filter_by(
            tor_ip = tor_ip).all()
    res = dict((t.tor_ip, t.sapi_tor_vsi_representation())
            for t in tt)
    return res

@utils.traceback_enable
def save_vsi(tor_ip, vsi_name):
    tt = SapiTorVsis(tor_ip = tor_ip,
            vsi_name = vsi_name)
    db.session.add(tt)
    db.session.commit()

@utils.traceback_enable
def delete_vsi(tor_ip, vsi_name):
    SapiTorVsis.query.filter_by(
            tor_ip = tor_ip,
            vsi_name = vsi_name).delete()
    db.session.commit()

@utils.traceback_enable
def delete_vsi_by_tor_ip(tor_ip):
    SapiTorVsis.query.filter_by(
            tor_ip = tor_ip).delete()
    db.session.commit()

class SapiTorTunnels(db.Model):
    __tablename__ = 'sapi_tor_tunnels'

    id = db.Column(db.INTEGER, primary_key = True, autoincrement=True)
    tor_ip = db.Column(db.String(db_constants.IP_ADDRESS_LENGTH))
    tunnel_id = db.Column(db.INTEGER)
    if_index = db.Column(db.INTEGER)
    dst_addr = db.Column(db.String(db_constants.IP_ADDRESS_LENGTH))

    def __init__(self, tor_ip, tunnel_id, if_index, dst_addr):
        self.tor_ip = tor_ip
        self.tunnel_id = tunnel_id
        self.if_index = if_index
        self.dst_addr = dst_addr

    def sapi_tor_tunnel_representation(self):
        return {'tor_ip': self.tor_ip,
                'tunnel_id': self.tunnel_id,
                'if_index': self.if_index,
                'dst_addr':self.dst_addr}

@utils.traceback_enable
def retrieve_tor_tunnel_by_dst_addr(dst_addr):
    tt = SapiTorTunnels.query.filter_by(
            dst_addr = dst_addr).all()
    res = dict((t.tor_ip, t.sapi_tor_tunnel_representation())
            for t in tt)
    return res

@utils.traceback_enable
def retrieve_tor_tunnels(tor_ip):
    tt = SapiTorTunnels.query.filter_by(
            tor_ip = tor_ip).all()
    res = dict((t.tunnel_id, t.sapi_tor_tunnel_representation())
            for t in tt)
    return res

@utils.traceback_enable
def save_tor_tunnel(tor_ip, tunnel_id, dst_addr, if_index=0):
    tt = SapiTorTunnels(tor_ip = tor_ip,
            tunnel_id = tunnel_id,
            dst_addr = dst_addr,
            if_index = if_index)
    db.session.add(tt)
    db.session.commit()

@utils.traceback_enable
def delete_tor_tunnel(tor_ip, tunnel_id):
    SapiTorTunnels.query.filter_by(
            tor_ip = tor_ip,
            tunnel_id = tunnel_id).delete()
    db.session.commit()

class SapiTor(db.Model):
    __tablename__ = 'sapi_tor'

    tor_ip = db.Column(db.String(db_constants.IP_ADDRESS_LENGTH), primary_key = True)
    tunnel_src_ip = db.Column(db.String(db_constants.IP_ADDRESS_LENGTH))

    def __init__(self, tor_ip, tunnel_src_ip):
        self.tor_ip = tor_ip
        self.tunnel_src_ip = tunnel_src_ip

    def sapi_tor_self_representation(self):
        return {'tor_ip': self.tor_ip,
                'tunnel_src_ip': self.tunnel_src_ip}

def retrieve_tor(tor_ip):
    try:
        tt = SapiTor.query.filter_by(
                tor_ip = tor_ip).one()
    except:
        return None
    return tt.sapi_tor_self_representation()

@utils.traceback_enable
def save_tor(tor_ip, tunnel_src_ip):
    tt = SapiTor(tor_ip = tor_ip, tunnel_src_ip = tunnel_src_ip)
    db.session.add(tt)
    db.session.commit()

@utils.traceback_enable
def delete_tor(tor_ip):
    SapiTor.query.filter_by(
            tor_ip = tor_ip).delete()
    db.session.commit()

@utils.traceback_enable
def retrieve_tors():
    tts = SapiTor.query.all()
    ret = dict((tt.tor_ip, tt.sapi_tor_self_representation())
            for tt in tts)
    return ret
