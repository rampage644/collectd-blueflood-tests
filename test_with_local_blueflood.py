#!/usr/bin/env python

import json
import pytest
import SocketServer
import subprocess
import threading
import time

import collectdconf
import http_server_mock

from twisted.internet import reactor, endpoints
from twisted.web import server


collectd_conf_in = 'collectd.conf.in'
collectd_conf = 'collectd.conf'
TIMEOUT = 0.5


def run_collectd(conf, wait=TIMEOUT):
    p = subprocess.Popen([collectdconf.collectd_bin, '-f', '-C', conf], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(TIMEOUT)
    p.terminate()
    return p.communicate(), p.returncode

def run_collectd_async(conf, cv=None):
    p = subprocess.Popen([collectdconf.collectd_bin, '-f', '-C', conf], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p


class TestRunCollectd:
    URL = ''
    AuthURL = ''

    @classmethod
    def setup_class(cls):
        # base collectd settings
        template = open(collectd_conf_in, 'r').read()
        # load write plugin
        write_blueflood_template = '''
<LoadPlugin write_blueflood>
    Interval %(interval)d
</LoadPlugin>

<Plugin write_blueflood>
    <URL "%(URL)s">
        TenantId    "%(tenantid)s"
        User        "%(user)s"
        Password    "%(password)s"
        AuthURL     "%(AuthURL)s"
        ttlInSeconds %(ttl)d
    </URL>
</Plugin>
'''

        with open(collectd_conf, 'w') as wfile:
            wfile.write(template % {
                    'base_dir': collectdconf.collectd_base_dir,
                    'pid_file': collectdconf.collectd_pid_file,
                    'plugin_dir': collectdconf.collectd_plugin_dir,
                    'types_file': collectdconf.collectd_types_file
                })

            wfile.write(write_blueflood_template % {
                    'URL': getattr(cls, 'URL', ''),
                    'AuthURL': getattr(cls, 'AuthURL', ''),
                    'user': getattr(cls, 'user', ''),
                    'password': getattr(cls, 'password', ''),
                    'tenantid': getattr(cls, 'tenantid', 'tenantid'),
                    'ttl': getattr(cls, 'ttl', 10),
                    'interval': getattr(cls, 'interval', 12)
                })

    def test_run_collectd(self):
        (out, err), code = run_collectd(collectd_conf)
        assert out != '', out
        assert 'Exiting normally' in out
        assert err == '', err
        assert code == 0

class TCPServerWithParams(SocketServer.TCPServer):

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, cv=None, data=None):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.cv = cv
        self.data = data



class TestRunCollectdLocalMocks(TestRunCollectd):
    URL = 'http://localhost:8000'
    AuthURL = 'http://localhost:8001'
    user = 'user1'
    password = 'pass2'

    def test_auth_is_done(self):
        acv = threading.Condition()
        bcv = threading.Condition()
        blueflood_data = ''
        b_handler = http_server_mock.BluefloodServerHandler(bcv)
        a_handler = http_server_mock.AuthServerHandler(acv)

        endpoints.serverFromString(reactor, "tcp:8000").listen(server.Site(b_handler))
        endpoints.serverFromString(reactor, "tcp:8001").listen(server.Site(a_handler))

        t = threading.Thread(target=reactor.run, args=(0, ))
        t.daemon = True
        t.start()

        p = run_collectd_async(collectd_conf)
        with acv:
            # wait for auth request
            acv.wait()
        assert len(a_handler.data) == 1, a_handler.data
        auth_data = json.loads(a_handler.data[0])
        assert auth_data['auth']['RAX-KSKEY:apiKeyCredentials'] == {'username': self.user, 'apiKey': self.password}
        with bcv:
            # wait for postdata from blueflood mock
            bcv.wait()
        assert len(b_handler.data) == 1, b_handler.data
        blueflood_data = json.loads(b_handler.data[0])
        assert type(blueflood_data) == list
        for element in blueflood_data:
            assert type(element) == dict
            assert 'collectionTime' in element
            assert type(element['collectionTime']) == int
            assert 'ttlInSeconds' in element
            assert type(element['ttlInSeconds']) == int
            assert 'metricValue' in element
            assert type(element['metricValue']) in (int, float)
            assert 'metricName' in element
            assert type(element['metricName']) in (str, unicode, bytes)

        # sanity checks
        assert len(a_handler.data) == 1
        assert len(b_handler.data) == 1
        # we've done
        p.terminate()
        print p.communicate()
        assert p.returncode == 0
