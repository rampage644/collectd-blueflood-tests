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
        print request.path, self, time.time()
        print dict(request.received_headers)
        data = request.content.read()
        print len(data)
        print ''
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

class Mock500ServerHandler(Mock401ServerHandler):
    def render_POST(self, request):
        resp = MockServerHandler.render_POST(self, request)
        resp = resp if self.count % self.frequency else ''
        self.count += 1
        return resp

if __name__ == '__main__':
    b_handler = MockServerHandler()
    a_handler = MockServerHandler()
    reauth_blue_handler = Mock401ServerHandler()
    error_blue_handler = Mock500ServerHandler()
    a_handler.response = """{"access":{"token":{"id":"eb5e1d9287054898a55439137ea68675","expires":"2014-12-14T22:54:49.574Z","tenant":{"id":"836986","name":"836986"}}}}"""
    endpoints.serverFromString(reactor, "tcp:8000").listen(server.Site(b_handler))
    endpoints.serverFromString(reactor, "tcp:8001").listen(server.Site(a_handler))
    endpoints.serverFromString(reactor, "tcp:8002").listen(server.Site(reauth_blue_handler))
    reactor.run()
