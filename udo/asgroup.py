import boto3
import sys
import time
from pprint import pprint

import config
import util
import launchconfig
import cluster

from time import sleep
from util import debug

_cfg = config.Config()

class AutoscaleGroup:
    def __init__(self, cluster_name, role_name):
        self.cluster_name = cluster_name
        self.role_name = role_name
        self.role_config = config.get_role_config(cluster_name, role_name)
        self.conn = util.as_conn()

    def name(self):
        debug("In asgroup.py name")
        return "-".join([self.cluster_name, self.role_name])

    def exists(self):
        debug("In asgroup.py exists")
        asg = self.get_asgroup()
        if asg:
            return asg
        return False

    def find_vpc_subnet_by_cidr(self, cidr):
        debug("In asgroup.py find_vpc_subnet_by_cidr")
        vpc = cluster.get_vpc_by_name(self.cluster_name)
        if not vpc:
            print "Failed to find VPC {}".format(self.cluster_name)
            return None
        # look for subnet that matches
        vpc_iterator = cluster.vpc_conn()
        vpc = None
        for _vpc in vpc_iterator:
          if _vpc.cidr_block == cidr:
              vpc = _vpc
        if not vpc:
            pprint("unable to find vpc with cidr " + str(cidr))
            return None
        return vpc

    # returns LaunchConfig for this ASgroup
    # may or may not exist
    def lc(self):
        debug("In asgroup.py lc")
        lc = launchconfig.LaunchConfig(self.cluster_name, self.role_name)
        if self.exists():
            asgroup = self.get_asgroup()
            if not asgroup:
                # NOTE:
                # this might be a race condition between 
                # exists() and get_asgroup()
                return None
            blc = asgroup['LaunchConfigurationName']
            #if blc:
            #    lc.set_name(blc)
            if 'LaunchConfigurationName' in blc:
                lc.set_name(blc)
        return lc

    # returns true if the LC exists
    def activate_lc(self):
        debug("In asgroup.py activate_lc")
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
        debug("In asgroup.py update_lc")
        oldlc = self.lc()
        #
        # NOTE:  Why does this try to delete the LaunchConfig ?
        lc = oldlc.update() # get new version

        asgroup = self.get_asgroup() # set lc
        asg_name = asgroup['AutoScalingGroupName']

        lcname = lc.name()
        
        client = util.as_conn()
        debug("updating asg: " + asg_name + " with LaunchConfig " + lcname)

        response = client.update_auto_scaling_group( AutoScalingGroupName = asg_name, LaunchConfigurationName = lcname )

        # delete old
        conn = util.as_conn()
        if oldlc.name() is not lcname:
            debug("deleting Launchconfig " + oldlc.name())
            conn.delete_launch_configuration ( LaunchConfigurationName = oldlc.name() )

    def get_asgroup(self):
        debug("In asgroup.py get_asgroup")
        conn = util.as_conn()
        asg = conn.describe_auto_scaling_groups( AutoScalingGroupNames = [ self.name() ] )
        if not asg['AutoScalingGroups']:
            return None
        else:
            asg = asg['AutoScalingGroups'][0]
        return asg

    def get_num_instances(self):
        ag = util.as_conn()
        asg_info = ag.describe_auto_scaling_groups( AutoScalingGroupNames = [ self.name() ] )
        return len(asg_info['AutoScalingGroups'][0]['Instances'])

    # get desired_size
    def get_scale_size(self):
        debug("In asgroup.py get_scale_size")
        asgroup = self.get_asgroup()
        print "Desired: {}\nMin:{}\nMax:{}".format(asgroup['DesiredCapacity'], asgroup['MinSize'], asgroup['MaxSize'])

    # set desired_size
    def scale(self, desired):
        debug("In asgroup.y scale")
        asgroup = self.get_asgroup()

        if desired < asgroup['MinSize']:
            print "Cannot scale: {} is lower than min_size ({})".format(desired, asgroup['MinSize'])
            return
        if desired > asgroup['MaxSize']:
            print "Cannot scale: {} is greater than max_size ({})".format(desired, asgroup['MaxSize'])
            if not util.confirm("Increase max_size to {}?".format(desired)):
                return
            asgroup['MaxSize'] = desired
        current = asgroup['DesiredCapacity']

        # Set DesiredCapacity
        response = util.as_conn().set_desired_capacity( AutoScalingGroupName = self.name(), DesiredCapacity = desired )

        # Check if DesiredCapacity was changed
        debug("in asgroup.py scale: running 'asgroup = self.get_asgroup()'")
        asgroup = self.get_asgroup()
        new = asgroup['DesiredCapacity']
        if (new != current):
            msg = "Changed ASgroup {} desired_capacity from {} to {}".format(self.name(), current, new)
            util.message_integrations(msg)

    # kill off asg and recreate it
    def reload(self):
        debug("In asgroup.py reload")
        if not util.confirm("Are you sure you want to tear down the {} ASgroup and recreate it?".format(self.name())):
            return
        util.message_integrations("Reloading ASgroup {}".format(self.name()))
        self.deactivate()
        #util.retry(lambda: self.activate(), 60)
        self.activate()

    def deactivate(self): # a.k.a asg destroy
        # NOTE
        # deleting asg logic should be in its own function

        # * delete ASG by reducing capacities of asg to 0
        # * delete launchconfig
        #
        # reducing ASG capacities to 0 triggers eventual instance
        # termination
        debug("In asgroup.py deactivate")        

        asg_name = self.name()
        ag = util.as_conn()
        ec2 = util.ec2_conn()
    
        asg_info = ag.describe_auto_scaling_groups( AutoScalingGroupNames = [ asg_name ] )

        if not asg_info['AutoScalingGroups']:
            print("ASG does not exist.  Maybe it was already deleted? ")
        else:
            # delete the ASG
            num_instances = len(asg_info['AutoScalingGroups'][0]['Instances'])
            if self.get_num_instances() == 0:
                pprint("There are no instances in asg: " + asg_name)
                pprint("Deleting asg: " + asg_name)
                response = ag.delete_auto_scaling_group( AutoScalingGroupName=asg_name )
                util.message_integrations("Deleted ASgroup {}".format(asg_name))
            else:
                debug("There are " + str(num_instances) + " instances that need to be removed from asg: " + asg_name)
                debug("terminating instances in asg: " + asg_name)
                debug("by setting to 0 MinSize, MaxSize, DesiredCapacity")
                response = ag.update_auto_scaling_group(AutoScalingGroupName = asg_name, MinSize=0, MaxSize=0, DesiredCapacity=0)
                debug("Waiting 30 seconds to give AWS time to terminate the instances")
                try:
                    sleep(30)
                except KeyboardInterrupt:
                    pprint("Got impatient.")
                interval = 10
                tries = 20
                for x in range(0,tries):
                    try:
                        if self.get_num_instances() != 0:
                            raise ValueError("there are still instances in the ASG")
                            break
                        else:
                            # if num instances in asg is 0,
                            # we are clear to delete
                            break
                    except KeyboardInterrupt:
                        pprint("Got impatient")
                    except ValueError as e:
                        pprint(e)
                        pass

                    try:
                        if e:
                            pprint("pausing " + str(interval) + " seconds")
                            sleep(interval)
                        else:
                            break
                    except KeyboardInterrupt:
                        pprint("Got impatient")
       
                if self.get_num_instances() == 0 or not self.get_num_instances():
                    pprint("instances in asg deleted.")
                    response = ag.delete_auto_scaling_group( AutoScalingGroupName=asg_name )
                    util.message_integrations("Deleted ASgroup {}".format(asg_name))
                else:
                    pprint("unable to delete instances in asg.")

        # if launch config exists, delete it 
        lc = self.lc()
        if not lc.exists():
            print("launchconfig does not exist.  Maybe you deleted it already?")
        else:
            lc.deactivate()

    def get_subnet_ids_by_cidrs(self, cidrs):
        debug("In asgroup.y get_subnet_ids_by_cidrs")
        ret = []
        _ec2 = util.ec2_conn()
        subnets = _ec2.describe_subnets()['Subnets']
        for cidr in cidrs:
            for subnet in subnets:
                if subnet['CidrBlock'] == cidr:
                    ret.append(subnet['SubnetId'])
        return ret

    # NOTE: Need to test with multiple availability zones and multiple subnet ids
    #
    # creates the LaunchConfig
    def activate(self):
        debug("In asgroup.py activate")
        conn = util.as_conn()
        cfg = self.role_config
        name = self.name()
        if not self.activate_lc(): # ensure this LaunchConfig already exists
            return False

        subnet_cidrs = cfg.get('subnets_cidr')
        if not subnet_cidrs or not len(subnet_cidrs) or None in subnet_cidrs:
            print "Valid subnets_cidr are required for {}/{}".format(self.cluster_name, self.role_name)
            return False
        print("Using subnets " + str(subnet_cidrs))

        subnet_ids = self.get_subnet_ids_by_cidrs(subnet_cidrs)
        azs=cfg.get('availability_zones')
        cfg_args = {}

        # If AvailabilityZones is defined, add it to the args we will pass to conn.create_auto_scaling_group()
        if azs:
            cfg_args['AvailabilityZones'] = azs
            print "AZs: {}".format(azs)
        else:
            pprint("No availability_zones set")

       # VPCZoneIdentifier ( which can be plural ) takes a string
        subnet_ids_string=''
        _length = len(subnet_ids)
        for subnet_id in subnet_ids:
            subnet_ids_string=subnet_ids_string + subnet_id
            if _length > 1:
                subnet_ids_string=subnet_ids_string + ', '
            _length = _length - 1
        pprint("Using subnet ids: " + str(subnet_ids_string))

        cfg_args['AutoScalingGroupName'] = self.name()
        cfg_args['DesiredCapacity'] = cfg.get('scale_policy')['desired']
        cfg_args['LoadBalancerNames'] = cfg.get('elbs')
        cfg_args['LaunchConfigurationName'] = self.lc().name()
        cfg_args['MaxSize'] = cfg.get('scale_policy', 'max_size')
        cfg_args['MinSize'] = cfg.get('scale_policy', 'min_size')
        cfg_args['VPCZoneIdentifier'] = subnet_ids_string

        if not cfg_args['LoadBalancerNames']:
            cfg_args['LoadBalancerNames'] = []

        response = conn.create_auto_scaling_group(**cfg_args)
        # NOTE: should check if asg was created

        debug('Preparing tags that will be applied to the asg')
        tags = cfg.get('tags')
        if not tags:
            tags = {}
        tags['cluster'] = self.cluster_name
        tags['role'] = self.role_name
        tags['Name'] = self.name()

        # apply tags        
        tag_set = [self.ag_tag(name, k,v) for (k,v) in tags.iteritems()]
        debug("Applying tags to asg")
        conn.create_or_update_tags(Tags=tag_set)

        util.message_integrations("Activated ASgroup {}".format(name))
        # NOTE: what should we be returning here?  Not sure.
        #return ag
        return name

    def ag_tag(self, ag, k, v):
        debug("In asgroup.py ag_tag")
        return { 'ResourceId': ag,
             'ResourceType': 'auto-scaling-group', # ResourceType must be string 'auto-scaling-group'
             'Key': str(k), # Key must be a string
             'Value': str(v), # Value must be a string
             'PropagateAtLaunch': True,
        }

    # NOTE: not sure what this is for. not sure what the token stuff is for
    def get_instances(self):
        debug("In asgroup.py get_instances")
        ret = []
        done = False
        next_token = None
        while not done:
            params = {}
            if next_token:
                params["next_token"] = next_token
            all_instances = self.conn.get_all_autoscaling_instances(**params)
            next_token = all_instances.next_token
            if not next_token:
                done = True
            instances = [i for i in all_instances if i.group_name == self.name()]
            ret.extend(instances)
        return ret

    def print_instances(self):
        debug("In asgroup.py print_instances")
        name = self.name()
        asg_info = self.conn.describe_auto_scaling_groups( AutoScalingGroupNames = [name] )['AutoScalingGroups']
        if not asg_info:
            pprint("No info for ASG " + name + " . are you sure it exists?")
            return None
        else:
            instances = asg_info[0]['Instances']
            print("Group\t\tID\t\tState\t\tStatus")
            for instance in instances:
                status = instance['HealthStatus']
                lcname = instance['LaunchConfigurationName']
                state = instance['LifecycleState']
                group = name
                iid = instance['InstanceId']
                print("{}\t{}\t{}\t{}".format(group, iid, state, status))

    def ip_addresses(self):
        debug("In asgroup.py ip_addresses")
        instances = self.conn.describe_auto_scaling_groups( AutoScalingGroupNames = [self.name()] )['AutoScalingGroups'][0]['Instances']
        ids = [i['InstanceId'] for i in instances]
        ec2_conn = util.ec2_conn()
        ec2_instances = ec2_conn.describe_instances( InstanceIds = ids )['Reservations']
        ips = [ instance['Instances'][0]['PublicIpAddress'] for instance in ec2_instances ]
        return ips
