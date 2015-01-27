#!/usr/bin/env python
# encoding: utf-8
import sys

from sapi import app
from neutron.common import config

config.init(sys.argv[1:])
host=app.config['HOST']
debug=app.config['DEBUG']
port=app.config['PORT']

app.run(host=host, debug=debug, port=port)
