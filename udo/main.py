#!/usr/bin/env python

import sys
import warnings
import os
import argparse
from pprint import pprint 

import config

import boto.ec2.autoscale
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup


# top-level commands go here
class Udo:
    def cluster(self, *args):
        print "Cluster: {}".format(args)




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
    method = Udo.__dict__.get(args.action)
    method(exe, args.action_args)
