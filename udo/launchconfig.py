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

class LCTemplate(Template):
    delimiter = '@'

class LaunchConfig:
    def __init__(self, cluster_name, role_name):
        self.cluster_name = cluster_name
        self.role_name = role_name
        self.role_config = _cfg.get_role_config(cluster_name, role_name)
        self.conn = util.as_conn()

    def name(self):
        return "-".join([self.cluster_name, self.role_name])

    # processes the script/cloud-init.sh template, returns a string
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

    # does a LC exist with our name?
    def exists(self):
        conn = util.as_conn()
        lcs = conn.get_all_launch_configurations(names = [self.name()])
        if len(lcs):
            return True
        return False

    # creates the LaunchConfig
    # returns True if LC exists
    def activate(self):
        conn = util.as_conn()
        conn = boto.ec2.autoscale.connect_to_region('us-west-2')

        name = self.name()

        # check if this LC already exists
        if self.exists():
            if not util.confirm("LaunchConfiguration {} already exists, overwrite? (y/n) ".format(name)):
                return True
            # delete existing
            conn.delete_launch_configuration(name)

        # get configuration for this LC
        cfg = self.role_config
        lc = LaunchConfiguration(
            name = name,
            image_id = cfg.get('ami'),
            instance_profile_name = cfg.get('iam_profile'),
            instance_type = cfg.get('instance_type'),
            security_groups = cfg.get('security_groups'),
            key_name = cfg.get('keypair_name'),
            user_data = self.cloud_init_script(),
            associate_public_ip_address = True,  # this is required for your shit to actually work
        )
        if not conn.create_launch_configuration(lc):
            print "Error creating launch configuration {}".format(name)
            return False

        return lc

