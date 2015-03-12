#!/usr/bin/env python
# encoding: utf-8

class BasicConfig(object):
    DEBUG = True
    VERSION = "0.0.1"
    APP_NAME = 'Sapi'
    HOST='localhost'

class ProductionConfig(BasicConfig):
    DEBUG = True
    PORT = 8080
    HOST='0.0.0.0'
    SSH_TIMEOUT = 20
    USERNAME = 'sinanp'
    PASSWORD = 'sinanp'
    SQLALCHEMY_DATABASE_URI = 'mysql://neutron:neutron@10.216.25.57/neutron'

class TestConfig(BasicConfig):
    PORT = 1919
