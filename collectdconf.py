#!/usr/bin/env python

import os

collectd_dir = '/home/ramp/git/collectd'
collectd_bin = os.path.join(collectd_dir, 'sbin', 'collectd')
collectd_conf = os.path.join(collectd_dir, 'etc', 'collectd.conf')
collectd_plugin_dir = os.path.join(collectd_dir, 'src', '.libs')
collectd_base_dir = os.path.join(collectd_dir, 'var')
collectd_pid_file = os.path.join(collectd_dir, 'collectd.pid')
collectd_types_file = os.path.join(collectd_dir, 'share', 'collectd', 'types.db')