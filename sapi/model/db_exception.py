#!/usr/bin/env python
# encoding: utf-8

from neutron.common import exceptions

class DBnotfounded(exceptions.NotFound):
    message = _('Db not found error')

class Multipledbfounded(exceptions.Conflict):
    message = _('Multiple row founded error')
