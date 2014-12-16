#!/usr/bin/env python

import collectdconf
import pytest
import subprocess
import time


collectd_conf_in = 'collectd.conf.in'
collectd_conf = 'collectd.conf'
TIMEOUT = 0.5


def run_collectd(conf, wait=TIMEOUT):
    p = subprocess.Popen([collectdconf.collectd_bin, '-f', '-C', conf], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(TIMEOUT)
    p.terminate()
    return p.communicate(), p.returncode


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
                    'user': 'user',
                    'password': 'pass',
                    'tenantid': 'tenant-id',
                    'ttl': 10,
                    'interval': 5
                })

    def test_run_collectd(file_collectd_conf):
        (out, err), code = run_collectd(collectd_conf)
        assert out != '', out
        assert err == '', err
        assert code == 0

class TestRunCollectdLocalMocks(TestRunCollectd):
    URL = 'http://localhost:8000'
    AuthURL = 'http://localhost:8001'



