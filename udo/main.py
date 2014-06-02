#!/usr/bin/env python

import sys
import warnings
import os
import argparse
from pprint import pprint 

import cluster

import boto.ec2.autoscale
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup


#####


# top-level commands go here
class Udo:
    def cluster(self, *args):
        action = args[0]
        if not action:
            print "Cluster command requires an action. Valid actions are: "
            print " list"
            return

        if action == 'list':
            cluster.list()
        return


#####


if __name__ == '__main__':
    # argument parsing
    parser = argparse.ArgumentParser(description='Manage AWS clusters.')
    parser.add_argument('action', metavar='action', type=str,
                       help='Action to perform. Valid actions: status.')
    parser.add_argument('action_args', metavar='args', type=str, nargs='*',
                       help='Additional arguments for action.')

    args = parser.parse_args()
    
    if args.action not in dir(Udo):
        print "{} is not a valid command".format(args.action)
        sys.exit(1)

    # execute action
    exe = Udo()
    method = getattr(exe, args.action)
    method(*args.action_args)
