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

class AutoscaleGroup:
    def __init__(self, cluster_name, role_name):
        self.cluster_name = cluster_name
        self.role_name = role_name
        self.role_config = _cfg.get_role_config(cluster_name, role_name)
        self.conn = util.as_conn()

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
        conn = util.as_conn()

        name = self.name()

        # ensure this LC already exists
        if not self.activate_lc():
            return False

        # does the ASgroup already exist?
        cfg = self.role_config
        print "AZs: {}".format(cfg.get('availability_zones'))
        ag = AutoScalingGroup(
            group_name=self.name(),
            load_balancers=cfg.get('elbs'),
            availability_zones=cfg.get('availability_zones'),
            vpc_zone_identifier=cfg.get('subnet'),
            launch_config=self.lc().name(),
            desired_capacity=cfg.get('scale_policy', 'desired'),
            min_size=cfg.get('scale_policy', 'min_size'),
            max_size=cfg.get('scale_policy', 'max_size'),
        )
        pprint(ag)
        if not conn.create_auto_scaling_group(ag):
            print "Failed to create autoscale group"
            return False

        return ag


