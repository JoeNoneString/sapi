#!/usr/bin/env python
# encoding: utf-8

import traceback
import logging
import socket
from flask import Response

LOG = None

def is_valid_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True

def register_api(app, view, endpoint, url, pk='id', pk_type='int'):
    view_func = view.as_view(endpoint)
    app.add_url_rule(url, defaults={pk: None},
                     view_func=view_func, methods=['GET',])
    app.add_url_rule(url, view_func=view_func, methods=['POST',])
    app.add_url_rule('%s<%s:%s>' % (url, pk_type, pk), view_func=view_func,
                     methods=['GET', 'PUT', 'DELETE'])

def init_logger(app):
    global LOG
    #formatter = logging.Formatter('[%(asctime)s] - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter("[%(asctime)s] -%(name)s- %(levelname)s : %(message)s",
                                          "%Y-%m-%d %H:%M:%S")
    floger = logging.FileHandler('log/sapi.log')
    floger.setLevel(logging.NOTSET)
    floger.setFormatter(formatter)
    app.logger.addHandler(floger)
    LOG = app.logger

def check_auth(auth):
    return auth.username == "admin" and auth.password == "admin"

def authenticate():
    return Response('Need proper authorization',
                    401,
                    {'WWW-Authenticate': 'Basic realm="Auth Required"'})

def traceback_enable(func):
    def inner_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            LOG.error(traceback.format_exc())
            raise ValueError("Internal Errors Occours")
    return inner_func

class LocalVLanBitmap(object):
    """Setup a VLAN bitmap for allocation or de-allocation."""

    def __init__(self, min, max):
        """Initialize the VLAN set."""
        self.min = min
        self.max = max
        self.size = self.get_array(max, True)
        self.array = [0 for i in range(self.size)]

    def __repr__(self):
        return "{\"LocalVLanBitmap\": \"%s\"}" %(self.array)

    def get_array(self, num, up=False):
        if up:
            return (num + 31 - 1) / 31
        return num / 31

    def get_bit_location(self, num):
        return num % 31

    def add_bits(self, num):
        """mask a bit"""
        elemIndex = self.get_array(num)
        byteIndex = self.get_bit_location(num)
        elem = self.array[elemIndex]
        self.array[elemIndex] = elem | (1 << (31 - byteIndex))

    def delete_bits(self, num):
        """Delete a in used bit."""
        elemIndex = self.get_array(num)
        byteIndex = self.get_bit_location(num)
        elem = self.array[elemIndex]
        self.array[elemIndex] = elem & (~(1 << (31 - byteIndex)))

    def get_unused_bits(self):
        """retrieve an unused vlan number"""
        for bits in range(self.min, self.max + 1):
            if self._bit_on(bits):
                continue
            self.add_bits(bits)
            return bits
        return None

    def _bit_on(self, bits):
        elemIndex = self.get_array(bits)
        byteIndex = self.get_bit_location(bits)
        if self.array[elemIndex] & (1 << (31 - byteIndex)):
            return True
        return False
