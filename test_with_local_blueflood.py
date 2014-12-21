#!/usr/bin/env python

import json
import pytest
import SocketServer
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

t = None 
b_handler = None
a_handler = None
reb_handler = None

def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    
    global b_handler, a_handler, reb_handler, t
    # blueflood server mock
    b_handler = http_server_mock.MockServerHandler()
    # auth server mock
    a_handler = http_server_mock.MockServerHandler()
    # blueflood mock sending 401 responses (for _re_auth scenario testing)
    reb_handler = http_server_mock.Mock401ServerHandler()

    endpoints.serverFromString(reactor, "tcp:8000").listen(server.Site(b_handler))
    endpoints.serverFromString(reactor, "tcp:8001").listen(server.Site(a_handler))
    endpoints.serverFromString(reactor, "tcp:8002").listen(server.Site(reb_handler))

    t = threading.Thread(target=reactor.run, args=(0, ))
    t.daemon = True
    t.start()

def teardown_module(module):
    """ teardown any state that was previously setup with a setup_module
    method.
    """
    global b_handler, a_handler, reb_handler, t

    reactor.stop()
    t = None

class TestRunCollectd:
    URL = ''
    AuthURL = ''

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
        <AuthURL     "%(AuthURL)s">
            User        "%(user)s"
            Password    "%(password)s"
        </AuthURL>
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
                    'tenantid': getattr(cls, 'tenantid', 'tenant-id'),
                    'ttl': getattr(cls, 'ttl', 600),
                    'interval': getattr(cls, 'interval', 5)
                })

        a_handler.data = []
        b_handler.data = []
        reb_handler.data = []


class TestJustRun(TestRunCollectd):

    def test_run_collectd(self):
        (out, err), code = run_collectd(collectd_conf)
        assert out != '', out
        assert 'Exiting normally' in out
        assert code == 0


class TestRunCollectdLocalMocks(TestRunCollectd):
    URL = 'http://localhost:8000'
    AuthURL = 'http://localhost:8001'
    user = 'user1'
    password = 'pass2'
    response = """{"access":{"token":{"id":"eb5e1d9287054898a55439137ea68675","expires":"2014-12-14T22:54:49.574Z","tenant":{"id":"836986","name":"836986"},"RAX-AUTH:authenticatedBy":["APIKEY"]},"serviceCatalog":[{"name":"cloudBlockStorage","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.blockstorage.api.rackspacecloud.com\\/v1\\/836986"}],"type":"volume"},{"name":"cloudImages","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.images.api.rackspacecloud.com\\/v2"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.images.api.rackspacecloud.com\\/v2"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.images.api.rackspacecloud.com\\/v2"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.images.api.rackspacecloud.com\\/v2"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.images.api.rackspacecloud.com\\/v2"}],"type":"image"},{"name":"cloudQueues","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-hkg.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-ord.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-syd.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-dfw.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-iad.queues.api.rackspacecloud.com\\/v1\\/836986"}],"type":"rax:queues"},{"name":"cloudBigData","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:bigdata"},{"name":"cloudOrchestration","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.orchestration.api.rackspacecloud.com\\/v1\\/836986"}],"type":"orchestration"},{"name":"cloudServersOpenStack","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/","versionId":"2"}],"type":"compute"},{"name":"autoscale","endpoints":[{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:autoscale"},{"name":"cloudDatabases","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.databases.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:database"},{"name":"cloudBackup","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.backup.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:backup"},{"name":"cloudMetrics","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/global.metrics.api.rackspacecloud.com\\/v2.0\\/836986"}],"type":"rax:cloudmetrics"},{"name":"cloudLoadBalancers","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:load-balancer"},{"name":"cloudMetricsIngest","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/global.metrics-ingest.api.rackspacecloud.com\\/v2.0\\/836986"}],"type":"rax:cloudmetrics"},{"name":"cloudNetworks","endpoints":[{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.networks.api.rackspacecloud.com\\/v2.0"}],"type":"network"},{"name":"cloudFeeds","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.hkg1.us.ci.rackspace.net\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.syd2.us.ci.rackspace.net\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.iad3.us.ci.rackspace.net\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.dfw1.us.ci.rackspace.net\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.ord1.us.ci.rackspace.net\\/836986"}],"type":"rax:feeds"},{"name":"cloudMonitoring","endpoints":[{"tenantId":"836986","publicURL":"https:\\/\\/monitoring.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:monitor"},{"name":"cloudDNS","endpoints":[{"tenantId":"836986","publicURL":"https:\\/\\/dns.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:dns"},{"name":"cloudFilesCDN","endpoints":[{"region":"ORD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"SYD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn4.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"DFW","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"HKG","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn6.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"IAD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn5.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"}],"type":"rax:object-cdn"},{"name":"cloudFiles","endpoints":[{"region":"ORD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.ord1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.ord1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"SYD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.syd2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.syd2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"DFW","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.dfw1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.dfw1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"IAD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.iad3.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.iad3.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"HKG","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.hkg1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.hkg1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"}],"type":"object-store"}],"user":{"id":"10040551","roles":[{"id":"10000351","description":"Creator role for Cloud Metrics access","name":"cloudmetrics:creator"},{"id":"3","description":"User Admin Role.","name":"identity:user-admin"},{"tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","id":"5","description":"A Role that allows a user access to keystone Service methods","name":"object-store:default"},{"tenantId":"836986","id":"6","description":"A Role that allows a user access to keystone Service methods","name":"compute:default"},{"id":"10000150","description":"Checkmate Access role","name":"checkmate"}],"name":"bf0testenv1","RAX-AUTH:defaultRegion":"ORD"}}}"""

    def test_auth_is_done(self):
        global b_handler, a_handler, t

        acv = threading.Condition()
        bcv = threading.Condition()
        blueflood_data = ''
        
        a_handler.cv = acv
        b_handler.cv = bcv
        a_handler.response = self.response

        p = run_collectd_async(collectd_conf)
        try:
            with acv:
                # wait for auth request
                acv.wait()
            assert len(b_handler.data) == 0
            assert len(a_handler.data) == 1, a_handler.data
            auth_data = json.loads(a_handler.data[0][3])
            assert auth_data['auth']['RAX-KSKEY:apiKeyCredentials'] == {'username': self.user, 'apiKey': self.password}, auth_data
            with bcv:
                # wait for postdata from blueflood mock
                bcv.wait()
            assert len(b_handler.data) == 1, b_handler.data
            assert 'X-Auth-Token'.lower() in b_handler.data[0][1]
            assert b_handler.data[0][1]['X-Auth-Token'.lower()] == json.loads(self.response)['access']['token']['id']
            assert b_handler.data[0][2] == '/v2.0/' + json.loads(self.response)['access']['token']['tenant']['id'] + '/ingest'
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

            # sanity checks
            assert len(a_handler.data) == 1
            assert len(b_handler.data) == 1
        finally:
            # we've done
            p.terminate()
            print 'Waiting process to terminate'
            p.wait()
            assert p.returncode == 0


class TestRunWithBluefloodNoAuth(TestRunCollectd):
    URL = 'http://localhost:19000'
    AuthURL = ''
    tenantid = 'tenant-id'

    def test_blueflood_ingest(self):
        p = run_collectd_async(collectd_conf)
        try:
            server = BluefloodEndpoint()
            server.tenant = self.tenantid

            resp = server.retrieve_resolution(collectdconf.test_metric_name, 0, int(time.time()*1000), 100)
            count_before = len(resp['values'])

            # wait for some time for collectd to write data to Blueflood
            time.sleep(15)
        
            resp = server.retrieve_resolution(collectdconf.test_metric_name, 0, int(time.time()*1000), 100)
            count_after = len(resp['values'][0])
            assert count_after > count_before, resp
            assert count_after != 0

        finally:
            p.terminate()
            print 'Waiting for collectd to terminate'
            p.wait()
            assert p.returncode == 0

class TestMockBluefloodNoAuth(TestRunCollectd):
    URL = 'http://localhost:8000'
    AuthURL = ''
    tenantid = 'tenant-id'

    def test_data_arrives(self):
        global b_handler, a_handler, t

        cv = threading.Condition()
        # blueflood server mock
        handler = b_handler
        handler.cv = cv

        p = run_collectd_async(collectd_conf)
        try:
            with cv:
                # wait for auth request
                cv.wait()

            assert len(handler.data) == 1
            assert 'X-Auth-Token'.lower() not in handler.data[0][1]
            assert handler.data[0][2] == '/v2.0/' + self.tenantid + '/ingest'
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
        finally:
            # we've done
            p.terminate()
            print 'Waiting for collectd to terminate'
            p.wait()
            assert p.returncode == 0

class TestBluefloodWithAuth(TestRunCollectd):
    URL = collectdconf.rax_url
    AuthURL = collectdconf.rax_auth_url
    user = collectdconf.rax_user
    password = collectdconf.rax_key

    def test_blueflood_ingest(self):
        p = run_collectd_async(collectd_conf)
        try:
            tenantid, token = authenticate(self.AuthURL, self.user, self.password)
            server = BluefloodEndpoint()
            server.tenant = tenantid.encode()
            server.headers = {'X-Auth-Token': token.encode()}
            server.ingest_url = collectdconf.rax_url
            server.retrieve_url = 'https://global.metrics.api.rackspacecloud.com'

            resp = server.retrieve_resolution(collectdconf.test_metric_name, 0, int(time.time()*1000))
            count_before = len(resp['values'])

            # wait for some time for collectd to write data to Blueflood
            time.sleep(15)
            
            resp = server.retrieve_resolution(collectdconf.test_metric_name, 0, int(time.time()*1000))
            count_after = len(resp['values'])
            assert count_after > count_before, resp
            assert count_after != 0
        finally:
            p.terminate()
            print 'Waiting for collectd to terminate'
            p.wait()
            assert p.returncode == 0

class TestBluefloodReauth(TestRunCollectd):
    URL = 'http://localhost:8002'
    AuthURL = 'http://localhost:8001'
    response = """{"access":{"token":{"id":"eb5e1d9287054898a55439137ea68675","expires":"2014-12-14T22:54:49.574Z","tenant":{"id":"836986","name":"836986"},"RAX-AUTH:authenticatedBy":["APIKEY"]},"serviceCatalog":[{"name":"cloudBlockStorage","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.blockstorage.api.rackspacecloud.com\\/v1\\/836986"}],"type":"volume"},{"name":"cloudImages","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.images.api.rackspacecloud.com\\/v2"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.images.api.rackspacecloud.com\\/v2"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.images.api.rackspacecloud.com\\/v2"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.images.api.rackspacecloud.com\\/v2"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.images.api.rackspacecloud.com\\/v2"}],"type":"image"},{"name":"cloudQueues","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-hkg.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-ord.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-syd.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-dfw.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-iad.queues.api.rackspacecloud.com\\/v1\\/836986"}],"type":"rax:queues"},{"name":"cloudBigData","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:bigdata"},{"name":"cloudOrchestration","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.orchestration.api.rackspacecloud.com\\/v1\\/836986"}],"type":"orchestration"},{"name":"cloudServersOpenStack","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/","versionId":"2"}],"type":"compute"},{"name":"autoscale","endpoints":[{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:autoscale"},{"name":"cloudDatabases","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.databases.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:database"},{"name":"cloudBackup","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.backup.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:backup"},{"name":"cloudMetrics","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/global.metrics.api.rackspacecloud.com\\/v2.0\\/836986"}],"type":"rax:cloudmetrics"},{"name":"cloudLoadBalancers","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:load-balancer"},{"name":"cloudMetricsIngest","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/global.metrics-ingest.api.rackspacecloud.com\\/v2.0\\/836986"}],"type":"rax:cloudmetrics"},{"name":"cloudNetworks","endpoints":[{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.networks.api.rackspacecloud.com\\/v2.0"}],"type":"network"},{"name":"cloudFeeds","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.hkg1.us.ci.rackspace.net\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.syd2.us.ci.rackspace.net\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.iad3.us.ci.rackspace.net\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.dfw1.us.ci.rackspace.net\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.ord1.us.ci.rackspace.net\\/836986"}],"type":"rax:feeds"},{"name":"cloudMonitoring","endpoints":[{"tenantId":"836986","publicURL":"https:\\/\\/monitoring.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:monitor"},{"name":"cloudDNS","endpoints":[{"tenantId":"836986","publicURL":"https:\\/\\/dns.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:dns"},{"name":"cloudFilesCDN","endpoints":[{"region":"ORD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"SYD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn4.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"DFW","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"HKG","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn6.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"IAD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn5.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"}],"type":"rax:object-cdn"},{"name":"cloudFiles","endpoints":[{"region":"ORD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.ord1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.ord1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"SYD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.syd2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.syd2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"DFW","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.dfw1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.dfw1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"IAD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.iad3.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.iad3.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"HKG","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.hkg1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.hkg1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"}],"type":"object-store"}],"user":{"id":"10040551","roles":[{"id":"10000351","description":"Creator role for Cloud Metrics access","name":"cloudmetrics:creator"},{"id":"3","description":"User Admin Role.","name":"identity:user-admin"},{"tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","id":"5","description":"A Role that allows a user access to keystone Service methods","name":"object-store:default"},{"tenantId":"836986","id":"6","description":"A Role that allows a user access to keystone Service methods","name":"compute:default"},{"id":"10000150","description":"Checkmate Access role","name":"checkmate"}],"name":"bf0testenv1","RAX-AUTH:defaultRegion":"ORD"}}}"""

    def test_reauth(self):
        global reb_handler, a_handler
        a_handler.response = self.response

        cv = threading.Condition()
        # blueflood server mock
        a_handler.cv = cv

        p = run_collectd_async(collectd_conf)
        try:
            print 'Waiting #1'
            with cv:
                cv.wait()
            # assert auth server hit
            assert len(a_handler.data) == 1

            print 'Waiting #2'
            with cv:
                cv.wait()
            # assert auth server wasn't hit yet
            assert len(a_handler.data) == 2
            assert len(reb_handler.data) == 3

        finally:
            # we've done
            p.terminate()
            print 'Waiting for collectd to terminate'
            p.wait()
            assert p.returncode == 0