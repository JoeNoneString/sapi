#!/usr/bin/env python
# encoding: utf-8

class BasicConfig(object):
    DEBUG = True
    VERSION = "0.1.0"
    APP_NAME = 'Sina SDN Controller(Fake)'
    HOST='localhost'

class ProductionConfig(BasicConfig):
    DEBUG = False
    PORT = 8080
    HOST='0.0.0.0'

class TestConfig(BasicConfig):
    PORT = 1919
