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
    response = """{"access":{"token":{"id":"eb5e1d9287054898a55439137ea68675","expires":"2014-12-14T22:54:49.574Z","tenant":{"id":"836986","name":"836986"},"RAX-AUTH:authenticatedBy":["APIKEY"]},"serviceCatalog":[{"name":"cloudBlockStorage","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.blockstorage.api.rackspacecloud.com\\/v1\\/836986"}],"type":"volume"},{"name":"cloudImages","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.images.api.rackspacecloud.com\\/v2"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.images.api.rackspacecloud.com\\/v2"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.images.api.rackspacecloud.com\\/v2"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.images.api.rackspacecloud.com\\/v2"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.images.api.rackspacecloud.com\\/v2"}],"type":"image"},{"name":"cloudQueues","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-hkg.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-ord.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-syd.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-dfw.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-iad.queues.api.rackspacecloud.com\\/v1\\/836986"}],"type":"rax:queues"},{"name":"cloudBigData","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:bigdata"},{"name":"cloudOrchestration","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.orchestration.api.rackspacecloud.com\\/v1\\/836986"}],"type":"orchestration"},{"name":"cloudServersOpenStack","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/","versionId":"2"}],"type":"compute"},{"name":"autoscale","endpoints":[{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:autoscale"},{"name":"cloudDatabases","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.databases.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:database"},{"name":"cloudBackup","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.backup.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:backup"},{"name":"cloudMetrics","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/global.metrics.api.rackspacecloud.com\\/v2.0\\/836986"}],"type":"rax:cloudmetrics"},{"name":"cloudLoadBalancers","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:load-balancer"},{"name":"cloudMetricsIngest","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/global.metrics-ingest.api.rackspacecloud.com\\/v2.0\\/836986"}],"type":"rax:cloudmetrics"},{"name":"cloudNetworks","endpoints":[{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.networks.api.rackspacecloud.com\\/v2.0"}],"type":"network"},{"name":"cloudFeeds","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.hkg1.us.ci.rackspace.net\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.syd2.us.ci.rackspace.net\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.iad3.us.ci.rackspace.net\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.dfw1.us.ci.rackspace.net\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.ord1.us.ci.rackspace.net\\/836986"}],"type":"rax:feeds"},{"name":"cloudMonitoring","endpoints":[{"tenantId":"836986","publicURL":"https:\\/\\/monitoring.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:monitor"},{"name":"cloudDNS","endpoints":[{"tenantId":"836986","publicURL":"https:\\/\\/dns.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:dns"},{"name":"cloudFilesCDN","endpoints":[{"region":"ORD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"SYD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn4.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"DFW","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"HKG","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn6.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"IAD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn5.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"}],"type":"rax:object-cdn"},{"name":"cloudFiles","endpoints":[{"region":"ORD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.ord1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.ord1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"SYD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.syd2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.syd2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"DFW","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.dfw1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.dfw1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"IAD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.iad3.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.iad3.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"HKG","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.hkg1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.hkg1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"}],"type":"object-store"}],"user":{"id":"10040551","roles":[{"id":"10000351","description":"Creator role for Cloud Metrics access","name":"cloudmetrics:creator"},{"id":"3","description":"User Admin Role.","name":"identity:user-admin"},{"tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","id":"5","description":"A Role that allows a user access to keystone Service methods","name":"object-store:default"},{"tenantId":"836986","id":"6","description":"A Role that allows a user access to keystone Service methods","name":"compute:default"},{"id":"10000150","description":"Checkmate Access role","name":"checkmate"}],"name":"bf0testenv1","RAX-AUTH:defaultRegion":"ORD"}}}"""

    def test_auth_is_done(self):
        acv = threading.Condition()
        bcv = threading.Condition()
        blueflood_data = ''
        # blueflood server mock
        b_handler = http_server_mock.MockServerHandler(bcv)
        # auth server mock
        a_handler = http_server_mock.MockServerHandler(acv)
        a_handler.response = self.response

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
        auth_data = json.loads(a_handler.data[0][2])
        assert auth_data['auth']['RAX-KSKEY:apiKeyCredentials'] == {'username': self.user, 'apiKey': self.password}
        with bcv:
            # wait for postdata from blueflood mock
            bcv.wait()
        assert len(b_handler.data) == 1, b_handler.data
        print b_handler.data
        assert 'X-Auth-Token' in b_handler.data[0][1]
        assert b_handler.data[0][1]['X-Auth-Token'] == json.loads(response)['access']['token']['id']
        blueflood_data = json.loads(b_handler.data[0][2])
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
