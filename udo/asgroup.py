import config
import util
import launchconfig

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

    def exists(self):
        ags = conn.get_all_groups(names = [self.name()])
        if len(ags):
            return True
        return False

    # returns LaunchConfig for this ASgroup
    # may or may not exist
    def lc(self):
        lc = launchconfig.LaunchConfig(self.cluster_name, self.role_name)
        return lc

    # returns true if the LC exists
    def activate_lc(self):
        # make sure we have a launchconfig activated
        lc = self.lc()
        if lc.exists():
            print "Using LaunchConfig {}".format(lc.name())
            return True
        print "Creating LaunchConfig {}".format(lc.name())
        return lc.activate()

    # creates the LaunchConfig
    def activate(self):
        conn = as_conn()
        conn = boto.ec2.autoscale.connect_to_region('us-west-2')

        name = self.name()

        # ensure this LC already exists
        if not self.activate_lc():
            return False

        # does the ASgroup already exist?


        return lc

