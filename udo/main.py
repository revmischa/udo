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
            return
        action = args.pop(0)

        # need cluster/role
        if len(args) < 2:
            print "Please specify cluster and role for any launchconfig command"
            return
        cluster = args.pop(0)
        role = args.pop(0)
        if not cluster or not role:
            print "launchconfig command requires a cluster and a role"
            return

        lc = launchconfig.LaunchConfig(cluster, role)

        if action == 'cloudinit':
            cloudinit = lc.cloud_init_script()
            print cloudinit
        elif action == 'activate':
            lc.activate()
        else:
            print "Unrecognized launchconfig action"


    # autoscale
    def asgroup(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "asgroup command requires an action. Valid actions are: "
            print " activate (cluster) (role) - create an autoscale group"
            return
        action = args.pop(0)

        # need cluster/role
        if len(args) < 2:
            print "Please specify cluster and role for any asgroup command"
            return
        cluster = args.pop(0)
        role = args.pop(0)
        if not cluster or not role:
            print "launchconfig command requires a cluster and a role"
            return

        ag = asgroup.AutoscaleGroup(cluster, role)

        if action == 'activate':
            ag.activate()
        elif action == 'deactivate':
            ag.deactivate()
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
  * cluster status (cluster) - view state of a cluster
  * cluster activate (cluster) - create a VPC
  * lc cloudinit (cluster) (role) - display cloud-init script
  * lc activate (cluster) (role) - create a launch configuration
  * asgroup list - list autoscaling groups
  * asgroup activate (cluster) (role) - create an autoscaling group
        """
        sys.exit(1)

    # execute cmd
    exe = Udo()
    method = getattr(exe, args.cmd)
    method(*args.cmd_args)
