#!/usr/bin/env python

import sys
import time
from twisted.web import resource

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
        return self.response

    def render_POST(self, request):
        request.setHeader('Content-type', 'application/json')
        if self.cv:
            with self.cv:
                self.data += [(time.time(), dict(request.received_headers), request.content.read())]
                self.cv.notify()
        return ''
