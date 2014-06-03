#!/usr/bin/env python

import sys
import warnings
import os
import argparse
from pprint import pprint

import cluster
import launchconfig

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
            else:
                print "Unknown cluster command: {}".format(action)
        return

    # launchconfig
    def lc(self, *args):
        args = list(args)
        if not len(args) or not args[0]:
            print "launchconfig command requires an action. Valid actions are: "
            print " cloudinit (cluster) (role) - view cloud_init bootstrap script"
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

#####


if __name__ == '__main__':
    # argument parsing
    parser = argparse.ArgumentParser(description='Manage AWS clusters.')
    parser.add_argument('action', metavar='action', type=str, nargs='?',
                       help='Action to perform. Valid actions: status.')
    parser.add_argument('action_args', metavar='args', type=str, nargs='*',
                       help='Additional arguments for action.')
    args = parser.parse_args()
    
    if args.action not in dir(Udo):
        if not args.action:
            args.action = ""
        print "'{}'' is not a valid command".format(args.action)
        print "\nValid commands are:"
        print " * cluster list"
        print " * lc cloudinit"
        sys.exit(1)

    # execute action
    exe = Udo()
    method = getattr(exe, args.action)
    method(*args.action_args)
