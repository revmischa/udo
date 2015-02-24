import config
import util
import launchconfig
import cluster

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
        self.role_config = config.get_role_config(cluster_name, role_name)
        self.conn = util.as_conn()

    def name(self):
        return "-".join([self.cluster_name, self.role_name])

    def exists(self):
        asg = self.get_asgroup()
        if asg:
            return asg
        return False

    def find_vpc_subnet_by_cidr(self, cidr):
        vpc = cluster.get_vpc_by_name(self.cluster_name)
        if not vpc:
            print "Failed to find VPC {}".format(self.cluster_name)
            return None
        # look for subnet that matches
        subnets = cluster.vpc_conn().get_all_subnets(
            filters=[
                ('cidrBlock', cidr),
                ('vpcId', vpc.id),
            ],
        )
        if len(subnets):
            return subnets[0]
        print "Failed to find subnet {}".format(cidr)
        return None

    # returns LaunchConfig for this ASgroup
    # may or may not exist
    def lc(self):
        lc = launchconfig.LaunchConfig(self.cluster_name, self.role_name)
        if self.exists():
            asgroup = self.get_asgroup()
            if not asgroup:
                return None  # this might be a race condition between exists() and get_asgroup()
            blc = asgroup.launch_config_name
            if blc:
                lc.set_name(blc)
        return lc

    # returns true if the LC exists
    def activate_lc(self):
        # make sure we have a launchconfig activated
        lc = self.lc()
        if not lc:
            # might need to wait a min
            util.retry(lambda: self.lc(), 60)
            lc = self.lc()
        if not lc:
            print "Timed out waiting to create LaunchConfiguration"
            return false
        if lc.exists():
            print "Using LaunchConfig {}".format(lc.name())
            return True
        print "Creating LaunchConfig {}".format(lc.name())
        return lc.activate()

    # we can't modify a launchconfig in place, we have to create
    # a new one and set that as our lc
    def update_lc(self):
        oldlc = self.lc()
        # get new version
        lc = oldlc.update()
        # set lc
        asgroup = self.get_asgroup()
        lcname = lc.name()
        setattr(asgroup, 'launch_config_name', lcname)
        asgroup.update()
        # delete old
        conn = util.as_conn()
        if oldlc.name() is not lcname:
            util.retry(lambda: conn.delete_launch_configuration(oldlc.name()), 60)

    def get_asgroup(self):
        conn = util.as_conn()
        ags = conn.get_all_groups(names = [self.name()])
        if not len(ags):
            return None
        return ags[0]

    # get desired_size
    def get_scale_size(self):
        asgroup = self.get_asgroup()
        print "Desired: {}\nMin:{}\nMax:{}".format(asgroup.desired_capacity, asgroup.min_size, asgroup.max_size)

    # set desired_size
    def scale(self, desired):
        asgroup = self.get_asgroup()

        if desired < asgroup.min_size:
            print "Cannot scale: {} is lower than min_size ({})".format(desired, asgroup.min_size)
            return
        if desired > asgroup.max_size:
            print "Cannot scale: {} is greater than max_size ({})".format(desired, asgroup.max_size)
            if not util.confirm("Increase max_size to {}?".format(desired)):
                return
            asgroup.max_size = desired

        current = asgroup.desired_capacity
        asgroup.desired_capacity = desired
        asgroup.update()
        asgroup = self.get_asgroup()
        new = asgroup.desired_capacity
        if (new != current):
            msg = "Changed ASgroup {} desired_capacity from {} to {}".format(self.name(), current, new)
            util.message_integrations(msg)

    # kill of ASgroup and recreate it
    def reload(self):
        if not util.confirm("Are you sure you want to tear down the {} ASgroup and recreate it?".format(self.name())):
            return
        util.message_integrations("Reloading ASgroup {}".format(self.name()))
        self.deactivate()
        util.retry(lambda: self.activate(), 60)

    def deactivate(self):
        if not self.exists():
            return
        ag = self.get_asgroup()
        ag.min_size = 0
        ag.max_size = 0
        ag.desired_capacity = 0
        ag.update()
        ag.shutdown_instances()
        print "Deleting... this may take a few minutes..."
        if util.retry(lambda: ag.delete(), 500):
            util.message_integrations("Deleted ASgroup {}".format(self.name()))
            # delete launchconfig too
            lc = self.lc()
            lc.deactivate()
        else:
            util.message_integrations("Failed to delete ASgroup {}".format(self.name()))

    # creates the LaunchConfig
    def activate(self):
        conn = util.as_conn()
        cfg = self.role_config
        name = self.name()

        # ensure this LC already exists
        if not self.activate_lc():
            return False

        # look up subnet id
        subnets = [self.find_vpc_subnet_by_cidr(cidr) for cidr in cfg.get('subnets_cidr')]
        if not subnets or not len(subnets) or None in subnets:
            print "Valid subnets_cidr are required for {}/{}".format(self.cluster_name, self.role_name)
            return False
        print "Using subnets {}".format(", ".join([s.id for s in subnets]))
        print "AZs: {}".format(cfg.get('availability_zones'))

        # does the ASgroup already exist?
        ag = AutoScalingGroup(
            group_name=self.name(),
            load_balancers=cfg.get('elbs'),
            availability_zones=cfg.get('availability_zones'),
            vpc_zone_identifier=[s.id for s in subnets],
            launch_config=self.lc().name(),
            desired_capacity=cfg.get('scale_policy', 'desired'),
            min_size=cfg.get('scale_policy', 'min_size'),
            max_size=cfg.get('scale_policy', 'max_size'),
        )

        if not conn.create_auto_scaling_group(ag):
            print "Failed to create autoscale group"
            return False

        # prepare instance tags
        tags = cfg.get('tags')
        if not tags:
            tags = {}
        tags['cluster'] = self.cluster_name
        tags['role'] = self.role_name
        tags['Name'] = self.name()

        # apply tags        
        tag_set = [self.ag_tag(ag, k,v) for (k,v) in tags.iteritems()]
        conn.create_or_update_tags(tag_set)

        util.message_integrations("Activated ASgroup {}".format(name))

        return ag

    def ag_tag(self, ag, k, v):
        return Tag(
            key=k,
            value=v,
            propagate_at_launch=True,
            resource_id=ag.name
        )
