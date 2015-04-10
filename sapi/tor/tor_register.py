#!/usr/bin/env python
# encoding: utf-8

from flask import Blueprint, request, render_template, redirect, url_for
from flask import current_app

from sapi import utils
from sapi import app
from sapi.tor import h3c
from sapi.tor import tor
from sapi.model import db_tor


register = Blueprint('register', __name__)


def validate(src, dst):
    if not utils.is_valid_ipv4_address(src):
        return "Invalid ipv4 address for tor ip \' %s \'" %(src)
    if not utils.is_valid_ipv4_address(dst):
        return "Invalid ipv4 address for tor tunnel ip \' %s \'" %(dst)

@register.route("/interface", methods=['GET', 'POST'])
def interface():
    conn = current_app._get_current_object().conn
    interfaces = None
    error = None

    if request.method == 'POST':
        torIp = request.form['torIp']

        try:
            interfaces = h3c.interface_info(conn[torIp])
        except KeyError:
            error = "Can`t connect to Tor \'%s\'" %(torIp)
        except:
            error = "查询失败"

    return render_template('interface.html', error=error, interfaces=interfaces)

@register.route("/torinfo", methods=['GET', 'POST'])
def tor_info():
    conn = current_app._get_current_object().conn
    if request.method == 'POST':
        torIp = request.form['torIp']
        app.logger.warning('Tunnel Sync : unregister tor \'%s\'' %(torIp))

        delete_tor = db_tor.retrieve_tor(torIp)
        db_tor.delete_tor_downlink(torIp)
        db_tor.delete_tor(torIp)
        db_tor.delete_vsi_by_tor_ip(torIp)

        #delete tunnels with in db tors
        other_tor_tunnels = db_tor.retrieve_tor_tunnel_by_dst_addr(delete_tor['tunnel_src_ip'])
        for tor_ip, tunnel_info in other_tor_tunnels.items():
            id = tunnel_info['tunnel_id']
            connection = conn[tor_ip]
            t = h3c.TUNNEL(connection, id)
            t.delete()
            db_tor.delete_tor_tunnel(tor_ip, id)
            app.logger.warning('Tunnel Sync : delete tunnel id \'%s\' on tor \'%s\', tunnel dst_addr \'%s\'' %(
                id, tor_ip, delete_tor['tunnel_src_ip']))

        #delete tunnels on delete tor
        delete_tor_tunnels = db_tor.retrieve_tor_tunnels(torIp)
        connection = conn[torIp]
        for id, tunnel_info in delete_tor_tunnels.items():
            t = h3c.TUNNEL(connection, id)
            t.delete()
            db_tor.delete_tor_tunnel(torIp, id)
            app.logger.warning('Tunnel Sync : delete tunnel id \'%s\' on tor \'%s\', tunnel dst_addr \'%s\'' %(
                id, torIp, tunnel_info['dst_addr']))

    tors = db_tor.retrieve_tors()
    for tor_ip in tors:
        downlinks = db_tor.retrieve_tor_downlink(tor_ip)
        tunnels = db_tor.retrieve_tor_tunnels(tor_ip)
        tors[tor_ip]['downlinks'] = downlinks['if_index_range']
        tors[tor_ip]['tunnels'] = [int(id) for id in tunnels]

    return render_template('boot.html', tors=[v for _, v in tors.items()])


@register.route("/register", methods=['GET', 'POST'])
def register_tor():
    conn = current_app._get_current_object().conn
    error = None

    if request.method == 'POST':
        torIp, srcIp = request.form['torIp'], request.form['srcIp']
        downlinks = request.form['downLinks']

        error = validate(torIp, srcIp)
        if not error and db_tor.retrieve_tor(torIp):
            error = "Existed tor ip \'%s\' in database." %(torIp)

        if not error:
            try:
                connection = conn[torIp]
            except:
                try:
                    conn[torIp] = tor.ConnTor(torIp,
                                app.config['USERNAME'],
                                app.config['PASSWORD'])
                except:
                    error = "Tor \'%s\' Connection Failed, Plz check it now !!!" %(torIp)

        if not error:
            app.logger.warning('Tunnel Sync : register new tor \'%s\', tunnel_src_ip \'%s\', downlinks \'%s\'' %(
                torIp, srcIp, downlinks))
            #existed tors in database
            other_tors = db_tor.retrieve_tors()

            #tunnel sync: config existed tors
            for other_tor_ip, tor_info in other_tors.items():
                connection = conn[other_tor_ip]
                id = h3c.get_avaliable_tunnel_id(connection)

                #create tunnel
                t = h3c.TUNNEL(connection, id, src_addr = tor_info['tunnel_src_ip'], dst_addr = srcIp)
                t.create()
                app.logger.warning('Tunnel Sync : create tunnel id \'%s\' on tor \'%s\', tunnel dst_addr \'%s\'' %(
                    id, other_tor_ip, srcIp))
                db_tor.save_tor_tunnel(other_tor_ip, id, srcIp)

                #get all vsis on tor (in db)
                vsis = db_tor.retrieve_vsis(other_tor_ip)
                for _, v in vsis.items():
                    vsiname = v['vsi_name']
                    vxlanid = int(vsiname[3:])
                    vxlan = h3c.VXLAN(connection, vxlanid)
                    vxlan.vsi_name = vsiname
                    vxlan.connect_vxlan_with_tunnel(id)
                    app.logger.warning('Tunnel Sync : edit vsi \'%s\' on tor \'%s\', connect with tunnel id \'%s\'' %(
                        vsiname, other_tor_ip, id))

            #tunnel sync: config registerd tor
            connection = conn[torIp]
            for other_tor_ip, tor_info in other_tors.items():
                id = h3c.get_avaliable_tunnel_id(connection)

                #create tunnel
                t = h3c.TUNNEL(connection, id, src_addr = srcIp, dst_addr = tor_info['tunnel_src_ip'])
                t.create()
                db_tor.save_tor_tunnel(torIp, id, tor_info['tunnel_src_ip'])
                app.logger.warning('Tunnel Sync : create tunnel id \'%s\' on tor \'%s\', tunnel dst_addr \'%s\'' %(
                    id, torIp, tor_info['tunnel_src_ip']))

            db_tor.save_tor(torIp, srcIp)
            db_tor.save_tor_downlink(torIp, downlinks)
            return redirect(url_for('register.tor_info'))

    return render_template('tor.html', error=error)
