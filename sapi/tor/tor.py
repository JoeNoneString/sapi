#!/usr/bin/env python
# encoding: utf-8

from ncclient import manager

class ConnTor(object):
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        try:
            self.conn = manager.connect_ssh(host = self.host,
                                        username = self.username,
                                        password = self.password,
                                        hostkey_verify = False,
                                        look_for_keys=False)
        except:
            self.conn = None
            raise ValueError("Tor Connection Init Failed.")

    def __enter__(self):
        if self.conn is None:
            raise ValueError("Tor Connection Error.")
        return self.conn

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_tb:
            self.conn = None

if __name__ == '__main__':
    with ConnTor('sw2', 'sinanp', 'sinanp') as m:
        print m.get_config(source='running')
