#!/usr/bin/env python

import os
import socket

collectd_dir = '/home/ramp/git/collectd'
collectd_bin = os.path.join(collectd_dir, 'sbin', 'collectd')
collectd_conf = os.path.join(collectd_dir, 'etc', 'collectd.conf')
collectd_plugin_dir = os.path.join(collectd_dir, 'lib', 'collectd')
collectd_base_dir = os.path.join(collectd_dir, 'var')
collectd_pid_file = os.path.join(collectd_dir, 'collectd.pid')
collectd_types_file = os.path.join(collectd_dir, 'share', 'collectd', 'types.db')

test_metric_name = '.'.join([socket.gethostname(), 'load', 'load', 'shortterm'])

rax_url = 'https://global.metrics-ingest.api.rackspacecloud.com'
rax_auth_url = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
rax_user = ''
rax_key = ''
