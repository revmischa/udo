import config
import util

import os
import sys
from pprint import pprint
from string import Template

import boto
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import LaunchConfiguration

_cfg = config.Config()

def as_conn():
    args = util.connection_args()
    return boto.ec2.autoscale.AutoScaleConnection(**args)

class LCTemplate(Template):
    delimiter = '@'

class LaunchConfig:
    def __init__(self, cluster_name, role_name):
        self.cluster_name = cluster_name
        self.role_name = role_name
        self.role_config = _cfg.get_role_config(cluster_name, role_name)
        if not self.role_config:
            print "{} is not a valid role in cluster {}".format(role_name, cluster_name)
            sys.exit(1)
            return
        self.conn = as_conn()

    def cloud_init_script(self):
        # load cloud-init script
        libdir = os.path.dirname(__file__)
        bootstrap_file = libdir + "/../script/cloud-init.sh"
        try:
            bootstrap = open(bootstrap_file).read()
        except IOError as err:
            print err
            sys.exit(1)

        cloud_init_template = LCTemplate(bootstrap)

        cloud_init_config = _cfg.get_root()

        # add extra template vars
        cloud_init_config['base_packages'] = " ".join(_cfg.get('packages'))
        cloud_init_config['role_packages'] = " ".join(self.role_config.get('packages'))
        cloud_init_config['repo_url'] = _cfg.get('repo', 'url')
        cloud_init_config['yum_plugin_url'] = _cfg.get('repo', 'plugin_url')

        # append extra commands from config
        cloud_init_extra = _cfg.get('cloud_init')
        if not cloud_init_extra:
            cloud_init_extra = ''
        cloud_init_config['cloud_init_extra'] = cloud_init_extra

        cloud_init = cloud_init_template.substitute(**cloud_init_config)
        return cloud_init

    # creates the LaunchConfig
    def activate(self):
        print self.cloud_init_script()
        return
