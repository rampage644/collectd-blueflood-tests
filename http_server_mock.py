#!/usr/bin/env python

import sys
import time
from twisted.web import resource, server
from twisted.internet import reactor, endpoints

class MockServerHandler(resource.Resource):
    isLeaf = True

    def __init__(self, cv=None):
        resource.Resource.__init__(self)
        # super(BluefloodServerHandler, self).__init__(self)
        self.cv = cv
        self.data = []
        self.response = ''

    def render_GET(self, request):
        request.setHeader("content-type", "text/plain")
        if self.cv:
            with self.cv:
                self.cv.notify()
        return ''

    def render_POST(self, request):
        request.setHeader('Content-type', 'application/json')
        # print request.path, self
        # print dict(request.received_headers)
        data = request.content.read()
        # print len(data), data
        # print ''
        if self.cv:
            with self.cv:
                self.data += [(time.time(), dict(request.received_headers), request.path, data)]
                self.cv.notify()
        else:
            self.data += [(time.time(), dict(request.received_headers), request.path, data)]

        return self.response

class Mock401ServerHandler(MockServerHandler):
    "Handler responses with 401 every 'self.frequency' time"
    isLeaf = True

    def __init__(self):
        MockServerHandler.__init__(self)
        self.count = 1
        self.frequency = 3

    def render_POST(self, request):
        resp = MockServerHandler.render_POST(self, request)
        code = 200 if self.count % self.frequency else 401
        self.count += 1
        request.setResponseCode(code)
        return resp

class Mock500ServerHandler(MockServerHandler):
    def render_POST(self, request):
        resp = MockServerHandler.render_POST(self, request)
        request.setResponseCode(500)
        return resp

if __name__ == '__main__':
    b_handler = MockServerHandler()
    a_handler = MockServerHandler()
    reauth_blue_handler = Mock401ServerHandler()
    error_blue_handler = Mock500ServerHandler()
    a_handler.response = """{"access":{"token":{"id":"eb5e1d9287054898a55439137ea68675","expires":"2014-12-14T22:54:49.574Z","tenant":{"id":"836986","name":"836986"},"RAX-AUTH:authenticatedBy":["APIKEY"]},"serviceCatalog":[{"name":"cloudBlockStorage","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.blockstorage.api.rackspacecloud.com\\/v1\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.blockstorage.api.rackspacecloud.com\\/v1\\/836986"}],"type":"volume"},{"name":"cloudImages","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.images.api.rackspacecloud.com\\/v2"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.images.api.rackspacecloud.com\\/v2"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.images.api.rackspacecloud.com\\/v2"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.images.api.rackspacecloud.com\\/v2"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.images.api.rackspacecloud.com\\/v2"}],"type":"image"},{"name":"cloudQueues","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-hkg.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-ord.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-syd.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-dfw.queues.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.queues.api.rackspacecloud.com\\/v1\\/836986","internalURL":"https:\\/\\/snet-iad.queues.api.rackspacecloud.com\\/v1\\/836986"}],"type":"rax:queues"},{"name":"cloudBigData","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.bigdata.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:bigdata"},{"name":"cloudOrchestration","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.orchestration.api.rackspacecloud.com\\/v1\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.orchestration.api.rackspacecloud.com\\/v1\\/836986"}],"type":"orchestration"},{"name":"cloudServersOpenStack","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/syd.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/dfw.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/iad.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/hkg.servers.api.rackspacecloud.com\\/","versionId":"2"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/v2\\/836986","versionInfo":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/v2","versionList":"https:\\/\\/ord.servers.api.rackspacecloud.com\\/","versionId":"2"}],"type":"compute"},{"name":"autoscale","endpoints":[{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.autoscale.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:autoscale"},{"name":"cloudDatabases","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.databases.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.databases.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:database"},{"name":"cloudBackup","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.backup.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.backup.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:backup"},{"name":"cloudMetrics","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/global.metrics.api.rackspacecloud.com\\/v2.0\\/836986"}],"type":"rax:cloudmetrics"},{"name":"cloudLoadBalancers","endpoints":[{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.loadbalancers.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:load-balancer"},{"name":"cloudMetricsIngest","endpoints":[{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/global.metrics-ingest.api.rackspacecloud.com\\/v2.0\\/836986"}],"type":"rax:cloudmetrics"},{"name":"cloudNetworks","endpoints":[{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.networks.api.rackspacecloud.com\\/v2.0"}],"type":"network"},{"name":"cloudFeeds","endpoints":[{"region":"HKG","tenantId":"836986","publicURL":"https:\\/\\/hkg.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.hkg1.us.ci.rackspace.net\\/836986"},{"region":"SYD","tenantId":"836986","publicURL":"https:\\/\\/syd.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.syd2.us.ci.rackspace.net\\/836986"},{"region":"IAD","tenantId":"836986","publicURL":"https:\\/\\/iad.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.iad3.us.ci.rackspace.net\\/836986"},{"region":"DFW","tenantId":"836986","publicURL":"https:\\/\\/dfw.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.dfw1.us.ci.rackspace.net\\/836986"},{"region":"ORD","tenantId":"836986","publicURL":"https:\\/\\/ord.feeds.api.rackspacecloud.com\\/836986","internalURL":"https:\\/\\/atom.prod.ord1.us.ci.rackspace.net\\/836986"}],"type":"rax:feeds"},{"name":"cloudMonitoring","endpoints":[{"tenantId":"836986","publicURL":"https:\\/\\/monitoring.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:monitor"},{"name":"cloudDNS","endpoints":[{"tenantId":"836986","publicURL":"https:\\/\\/dns.api.rackspacecloud.com\\/v1.0\\/836986"}],"type":"rax:dns"},{"name":"cloudFilesCDN","endpoints":[{"region":"ORD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"SYD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn4.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"DFW","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"HKG","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn6.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"IAD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/cdn5.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"}],"type":"rax:object-cdn"},{"name":"cloudFiles","endpoints":[{"region":"ORD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.ord1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.ord1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"SYD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.syd2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.syd2.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"DFW","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.dfw1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.dfw1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"IAD","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.iad3.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.iad3.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"},{"region":"HKG","tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","publicURL":"https:\\/\\/storage101.hkg1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","internalURL":"https:\\/\\/snet-storage101.hkg1.clouddrive.com\\/v1\\/MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001"}],"type":"object-store"}],"user":{"id":"10040551","roles":[{"id":"10000351","description":"Creator role for Cloud Metrics access","name":"cloudmetrics:creator"},{"id":"3","description":"User Admin Role.","name":"identity:user-admin"},{"tenantId":"MossoCloudFS_3d820fe1-52a8-4315-b1de-67f4bfff3001","id":"5","description":"A Role that allows a user access to keystone Service methods","name":"object-store:default"},{"tenantId":"836986","id":"6","description":"A Role that allows a user access to keystone Service methods","name":"compute:default"},{"id":"10000150","description":"Checkmate Access role","name":"checkmate"}],"name":"bf0testenv1","RAX-AUTH:defaultRegion":"ORD"}}}"""
    endpoints.serverFromString(reactor, "tcp:8000").listen(server.Site(b_handler))
    endpoints.serverFromString(reactor, "tcp:8001").listen(server.Site(a_handler))
    endpoints.serverFromString(reactor, "tcp:8002").listen(server.Site(reauth_blue_handler))
    endpoints.serverFromString(reactor, "tcp:8003").listen(server.Site(error_blue_handler))
    reactor.run()
