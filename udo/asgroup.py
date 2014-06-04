import config
import util

from pprint import pprint

import boto
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import AutoScalingGroup
from boto.ec2.autoscale import ScalingPolicy
from boto.ec2.autoscale import Tag

_cfg = config.Config()

def as_conn():
    args = util.connection_args()
    return boto.ec2.autoscale.AutoScaleConnection(**args)

class LaunchConfig:
    def __init__(self, cluster_name, role_name):
        self.cluster_name = cluster_name
        self.role_name = role_name
        self.role_config = _cfg.get_role_config(cluster_name, role_name)
        self.conn = as_conn()

    def name(self):
        return "-".join([self.cluster_name, self.role_name])

    # creates the LaunchConfig
    def activate(self):
        conn = as_conn()
        conn = boto.ec2.autoscale.connect_to_region('us-west-2')

        name = self.name()

        # check if this LC already exists
        lcs = conn.get_all_launch_configurations(names = [name])
        if len(lcs):
            if not util.confirm("LaunchConfiguration {} already exists, overwrite? (y/n) ".format(name)):
                return
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

        return lc

