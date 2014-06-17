#!/usr/bin/env python

import sys
import warnings
import os
import argparse
from pprint import pprint

import cluster
import launchconfig
import util
import asgroup
import config

import boto.ec2.autoscale
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup


#####


# top-level commands go here
class Udo:
    def cluster(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "cluster command requires an action. Valid actions are: "
            print " list\n status"
            return
        action = args.pop(0)

        if action == 'list':
            cluster.list()
        else:
            # actions that require a cluster name
            if not len(args) or not args[0]:
                print "cluster name required for {}".format(action)
                return
            cluster_name = args.pop(0)
            cl = cluster.Cluster(cluster_name)
            if action == 'status':
                print "{} status: {}".format(cluster_name, cl.status())
            elif action == 'activate':
                if not cl.activate():
                    print "Failed to bring up {} cluster".format(cluster_name)
            else:
                print "Unknown cluster command: {}".format(action)


    # launchconfig
    def lc(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "launchconfig command requires an action. Valid actions are: "
            print " cloudinit (cluster) (role) - view cloud_init bootstrap script"
            print " activate (cluster) (role) - create launch configuration"
            print " deactivate (cluster) (role) - delete launch configuration"
            return
        action = args.pop(0)

        cluster,role = self.get_cluster_and_role_from_args(*args)
        if not cluster or not role:
            return

        lc = launchconfig.LaunchConfig(cluster, role)

        if action == 'cloudinit':
            cloudinit = lc.cloud_init_script()
            print cloudinit
        elif action == 'activate':
            lc.activate()
        elif action == 'deactivate':
            lc.deactivate()
        else:
            print "Unrecognized launchconfig action"


    # autoscale
    def asg(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "asgroup command requires an action. Valid actions are: "
            print " activate (cluster) (role) - create an autoscale group"
            print " deactivate (cluster) (role) - delete an autoscale group and terminate all instances"
            print " reload (cluster) (role) - deactivates asgroup and launchconfig, then recreates them"
            print " updatelc (cluster) (role) - generates a new launchconfig version"
            return
        action = args.pop(0)

        # TODO: hook up 'list'

        cluster,role = self.get_cluster_and_role_from_args(*args)
        if not cluster or not role:
            return

        ag = asgroup.AutoscaleGroup(cluster, role)

        if action == 'activate':
            ag.activate()
        elif action == 'deactivate':
            ag.deactivate()
        elif action == 'reload':
            ag.reload()
        elif action == 'updatelc':
            ag.update_lc()
        else:
            print "Unrecognized asgroup action"


    # for testing features
    def test(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "test command requires an action. Valid actions are: "
            print " integrations"
            return
        action = args.pop(0)

        if action == 'integrations':
            util.message_integrations("Testing Udo integrations")
        else:
            print "Unknown test command: {}".format(action)

    def get_cluster_and_role_from_args(self, *args):
        args = list(args)

        # need cluster/role
        if len(args) < 1:
            print "Please specify cluster name for this command"
            return None,None
        cluster = args.pop(0)

        # use role name if specified, otherwise assume they meant the obvious thing
        # if there's only one role
        if len(args):
            role = args.pop(0)
        else:
            roles = config.get_cluster_config(cluster).get('roles')
            if not roles:
                print "Cluster config for {} not found".format(cluster)
                return None,None

            rolenames = roles.keys()
            if len(rolenames) == 1:
                # assume the only role
                print "No role specified, assuming {}".format(rolenames[0])
                role = rolenames[0]
            else:
                print "Multiple roles available for cluster {}".format(cluster)
                for r in rolenames:
                    print "  - {}".format(r)
                return None,None

        return cluster, role
#####


if __name__ == '__main__':
    # argument parsing
    parser = argparse.ArgumentParser(description='Manage AWS clusters.')
    parser.add_argument('cmd', metavar='command', type=str, nargs='?',
                       help='Action to perform. Valid actions: status.')
    parser.add_argument('cmd_args', metavar='args', type=str, nargs='*',
                       help='Additional arguments for command.')
    args = parser.parse_args()
    
    if args.cmd not in dir(Udo):
        if not args.cmd:
            args.cmd = ""
        print "'{}' is not a valid command".format(args.cmd)
        print """
Valid commands are:
  * cluster list - view state of clusters
  * cluster status - view state of a cluster
  * cluster activate - create a VPC
  * lc cloudinit - display cloud-init script
  * lc activate - create a launch configuration
  * lc deactivate - delete a launch configuration
  * asg reload - deactivate and activate an autoscaling group to update the config
  * asg activate - create an autoscaling group
  * asg deactivate - delete an autoscaling group
  * asg updatelc - updates launchconfiguration in-place
        """
        sys.exit(1)

    # execute cmd
    exe = Udo()
    method = getattr(exe, args.cmd)
    method(*args.cmd_args)
