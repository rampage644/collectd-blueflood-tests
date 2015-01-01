#!/usr/bin/env python

import json
import pytest
import SocketServer
import socket
import subprocess
import threading
import time
import urllib2

from blueflood_python.blueflood import BluefloodEndpoint

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

def authenticate(url, user, key):
    adata = '{"auth": {"RAX-KSKEY:apiKeyCredentials": {"username": "%s", "apiKey": "%s"}}}' % (user, key)

    req = urllib2.Request(url, adata, {'Content-Type': 'application/json'})
    resp = urllib2.urlopen(req)
    resp = json.loads(resp.read())
    token = resp['access']['token']['id']
    tenant = resp['access']['token']['tenant']['id']
    return tenant, token

b_handler = None
b_handler_port = None 
a_handler = None

def setup_listnening_port(data):
    global b_handler_port
    b_handler_port = data

def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    
    global b_handler, a_handler, reb_handler, err_handler, t
    # blueflood server mock
    b_handler = http_server_mock.MockServerHandler()
    # auth server mock
    a_handler = http_server_mock.MockServerHandler()

    endpoints.serverFromString(reactor, "tcp:8000").listen(server.Site(b_handler)).addCallback(setup_listnening_port)
    endpoints.serverFromString(reactor, "tcp:8001").listen(server.Site(a_handler))

    t = threading.Thread(target=reactor.run, args=(0, ))
    t.daemon = True
    t.start()

def teardown_module(module):
    """ teardown any state that was previously setup with a setup_module
    method.
    """
    global b_handler, a_handler, t

    reactor.stop()
    t = None

class TestRunCollectd:
    URL = 'http://localhost:8000'
    AuthURL = 'http://localhost:8001'
    interval = 10

    @classmethod
    def setup_class(cls):
        global a_handler, b_handler
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
        ttlInSeconds %(ttl)d
        %(auth_template)s
    </URL>
</Plugin>
'''
        write_blueflood_auth_template = '''
        <AuthURL     "%(AuthURL)s">
            User        "%(user)s"
            Password    "%(password)s"
        </AuthURL>
'''

        with open(collectd_conf, 'w') as wfile:
            wfile.write(template % {
                    'base_dir': collectdconf.collectd_base_dir,
                    'pid_file': collectdconf.collectd_pid_file,
                    'plugin_dir': collectdconf.collectd_plugin_dir,
                    'types_file': collectdconf.collectd_types_file
                })
            auth_template = write_blueflood_auth_template % {
                    'AuthURL': getattr(cls, 'AuthURL', ''),
                    'user': getattr(cls, 'user', ''),
                    'password': getattr(cls, 'password', '')
            }
            wfile.write(write_blueflood_template % {
                    'URL': getattr(cls, 'URL', ''),
                    'auth_template': auth_template if getattr(cls, 'AuthURL', '') else '',
                    'tenantid': getattr(cls, 'tenantid', 'tenant-id'),
                    'ttl': getattr(cls, 'ttl', 600),
                    'interval': getattr(cls, 'interval', 5)
                })


@pytest.fixture
def collectd(request):
    p = run_collectd_async(collectd_conf)
    minimum_run_time = 1
    start_time = time.time()
    def fin():
        stop_time = time.time()
        # wait collectd to run for minimum time
        # needed for proper signal handling
        while stop_time - start_time < minimum_run_time:
            time.sleep(0.1)
            stop_time = time.time()
        p.terminate()
        print 'Waiting process to terminate'
        watchdog_timer = threading.Timer(5.0, p.kill, [p])
        watchdog_timer.start()
        p.wait()
        watchdog_timer.cancel()
        assert p.returncode == 0

    request.addfinalizer(fin)
    return p

@pytest.fixture
def blueflood_handler(request):
    global b_handler
    cv = threading.Condition()
    b_handler.cv = cv
    def fin():
        b_handler.reset_to_default_reply()
        b_handler.cv = None
        b_handler.data = []
    request.addfinalizer(fin)
    return b_handler

@pytest.fixture
def auth_handler(request):
    global a_handler
    cv = threading.Condition()
    a_handler.cv = cv
    def fin():
        a_handler.reset_to_default_reply()
        a_handler.cv = None
        a_handler.data = []
    request.addfinalizer(fin)
    return a_handler


class TestRunCollectdLocalMocks(TestRunCollectd):
    user = 'user1'
    password = 'pass2'
    response = """{"access":{"token":{"id":"eb5e1d9287054898a55439137ea68675","expires":"2014-12-14T22:54:49.574Z","tenant":{"id":"836986","name":"836986"}}}}"""
    interval = 10
    tenantid = 'tenant-id'

    def test_auth_is_done(self, blueflood_handler, auth_handler, collectd):
        acv = auth_handler.cv
        auth_handler.should_reply_forever(200, self.response, {})
        bcv = blueflood_handler.cv
        blueflood_data = ''

        print 'Waiting for auth post'
        with bcv:
            # wait for auth request
            bcv.wait(self.interval * 2)
        assert len(a_handler.data) == 1, a_handler.data
        assert len(b_handler.data) == 1, b_handler.data

        auth_data = json.loads(a_handler.data[0][3])
        assert auth_data['auth']['RAX-KSKEY:apiKeyCredentials'] == {'username': self.user, 'apiKey': self.password}, auth_data

        assert 'X-Auth-Token'.lower() in b_handler.data[0][1]
        assert b_handler.data[0][1]['X-Auth-Token'.lower()] == json.loads(self.response)['access']['token']['id']
        assert b_handler.data[0][2] == '/v2.0/' + self.tenantid + '/ingest'
        blueflood_data = json.loads(b_handler.data[0][3])
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


class TestRunWithBluefloodNoAuth(TestRunCollectd):
    URL = 'http://localhost:19000'
    AuthURL = ''
    tenantid = 'tenant-id'

    def test_blueflood_ingest(self, collectd):
        try:
            blueflood_socket = socket.socket()
            blueflood_socket.connect(*urllib2.splitport(self.URL))
        except:
            pytest.skip()

        server = BluefloodEndpoint()
        server.tenant = self.tenantid

        resp = server.retrieve_resolution(collectdconf.test_metric_name, 0, int(time.time()*1000))
        count_before = len(resp['values'])

        # wait for some time for collectd to write data to Blueflood
        time.sleep(15)
    
        resp = server.retrieve_resolution(collectdconf.test_metric_name, 0, int(time.time()*1000))
        count_after = len(resp['values'][0])
        assert count_after > count_before, resp
        assert count_after != 0


class TestMockBluefloodNoAuth(TestRunCollectd):
    AuthURL = ''
    tenantid = 'tenant-id'
    interval = 5

    def test_data_arrives(self, blueflood_handler, collectd):
        cv = blueflood_handler.cv
        # blueflood server mock
        handler = blueflood_handler

        with cv:
            cv.wait(self.interval * 2)

        assert len(handler.data) == 1
        assert 'X-Auth-Token'.lower() not in handler.data[0][1]
        assert handler.data[0][2] == '/v2.0/' + self.tenantid + '/ingest'
        print handler.data
        blueflood_data = json.loads(handler.data[0][3])
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

    def test_data_arrival_interval(self, blueflood_handler, collectd):
        cv = blueflood_handler.cv
        # blueflood server mock
        handler = blueflood_handler

        counter = 0
        with cv:
            # wait for 3 POST data
            while counter < 3:
                cv.wait(self.interval * 2)
                counter += 1

        assert len(handler.data) == 3
        # will discard first one as it could happen at start
        # and we need only interval called
        prev_time = handler.data[1][0]
        for index in range(2, len(handler.data)):
            time = handler.data[index][0]
            print prev_time, time, (time - prev_time), 
            assert float(self.interval) * (1 - 0.01) < abs(time - prev_time) < float(self.interval) * (1 + 0.01)
            prev_time = time

class TestErrorBluefloodNoAuth(TestRunCollectd):
    AuthURL = ''
    tenantid = 'tenant-id'

    def _parse_data_into_metrics(self, data):
        """
        return dict {key:metric name, value: [time1, time2, timeN] }
        """
        return_dict = {}
        series = json.loads(data)
        for metric in series:
            times = return_dict.get(metric['metricName'], [])
            times.append(metric['collectionTime'])
            return_dict[metric['metricName']] = times
        return return_dict

    def test_error_response(self, blueflood_handler, collectd):
        global b_endpoint, b_handler_port
        cv = blueflood_handler.cv

        # we start by disabling data ingestion. Idea is that after we enable it
        # again we should recieve all data including data from this specific
        # interval
        not_recieve_data_start_time = int(time.time())
        # stop listening right now
        b_handler_port.stopListening()
        # wait for some time
        time.sleep(self.interval * 2)
        # start listening again
        b_handler_port.startListening()
        not_recieve_data_end_time = int(time.time())


        with cv:
            cv.wait(self.interval * 2)
        assert len(blueflood_handler.data) == 1
        
        data = self._parse_data_into_metrics(blueflood_handler.data[0][3])
        times = data[collectdconf.test_metric_name]
        for collectionTime in times:
            if not_recieve_data_start_time <= int(collectionTime * 0.001)\
             <= not_recieve_data_end_time:
                # as soon as we find _ANY_ point that fits 'rejecting' interval
                # we stop cause it proves we're been supplied with data from
                # 'rejecting' interval
                return
        # if we did not exit before, fail
        assert False
        

class TestBluefloodWithAuth(TestRunCollectd):
    URL = collectdconf.rax_url
    AuthURL = collectdconf.rax_auth_url
    user = collectdconf.rax_user
    password = collectdconf.rax_key
    tenantid = '836986'

    def test_blueflood_ingest(self, collectd):
        tenantid, token = authenticate(self.AuthURL, self.user, self.password)
        server = BluefloodEndpoint()
        server.tenant = tenantid.encode()
        server.headers = {'X-Auth-Token': token.encode()}
        server.ingest_url = collectdconf.rax_url
        server.retrieve_url = 'https://global.metrics.api.rackspacecloud.com'

        resp = server.retrieve_resolution(collectdconf.test_metric_name, 0, int(time.time()*1000))
        count_before = len(resp['values'])

        # wait for some time for collectd to write data to Blueflood
        time.sleep(self.interval * 3 + 1)
        
        resp = server.retrieve_resolution(collectdconf.test_metric_name, 0, int(time.time()*1000))
        count_after = len(resp['values'])
        assert count_after > count_before, resp
        assert count_after != 0

class TestBluefloodReauth(TestRunCollectd):
    response = """{"access":{"token":{"id":"eb5e1d9287054898a55439137ea68675","expires":"2014-12-14T22:54:49.574Z","tenant":{"id":"836986","name":"836986"}}}}"""
    interval = 5

    def test_reauth(self, blueflood_handler, auth_handler, collectd):
        auth_handler.should_reply_forever(200, self.response, {})
        blueflood_handler.should_reply_once(200, '', {})
        blueflood_handler.should_reply_once(200, '', {})
        blueflood_handler.should_reply_once(401, '', {})
        cv = auth_handler.cv

        print 'Waiting #1'
        with cv:
            cv.wait(self.interval * 2)
        # assert auth server hit
        assert len(a_handler.data) == 1

        print 'Waiting #2'
        with cv:
            cv.wait(self.interval * 4)
        assert len(a_handler.data) == 2
        assert len(blueflood_handler.data) == 4
