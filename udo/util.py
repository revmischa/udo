# Handy common utilities for udo modules

import config
import boto
import json
import urllib2
from time import sleep
import sys
import os
import socket
import getpass

# don't use for tests
def default_config():
    return config.Config()

def region():
    return default_config().get('region')

# returns dict of arguments common to any boto connection we establish
def connection_args():
    _region = region()
    if not _region:
        # use the default region, I guess?
        print "Warning: default region is not configured"
        return "us-east-1"

    args = {
        'region': boto.ec2.get_region(_region)
    }
    return args

# autoscale connection
def as_conn():
    args = connection_args()
    region = args.pop('region')
    return boto.ec2.autoscale.connect_to_region(region.name, **args)

# codedeploy connection
def deploy_conn():
    args = connection_args()
    region = args.pop('region')
    return boto.codedeploy.connect_to_region(region.name, **args)

# ask a yes/no question
# returns true/false
def confirm(msg):
    yn = raw_input(msg + " (y/n) ")
    if yn.lower() == 'y':
        return True
    print "Aborted"
    return False

# keep trying proc until timeout or no exception is thrown
# use this when you're waiting for a change to take effect
# FIXME: actually respect timeout
def retry(proc, timeout):
    success = False
    ret = None
    while success == False:
        try:
            ret = proc()     
            success = True
        except boto.exception.BotoServerError as e:
            if default_config().get('debug'):
                # dump response
                print "Error: {}, retrying...".format(e)
            else:
                print('.'),
            sys.stdout.flush()
            sleep(5)
    print "\n"
    return ret

def user_and_host():
    username = getpass.getuser()
    hostname = socket.gethostname()
    return "{}@{}".format(username, hostname)

# also prints out msg
def message_integrations(msg):
    message_slack("[{}]  {}".format(user_and_host(), msg))
    print msg

def message_slack(msg):
    slack_cfg = default_config().new_root('slack')
    if not slack_cfg:
        # not configured
        return

    slack_url      = slack_cfg.get('url')
    slack_username = slack_cfg.get('username')
    slack_channel  = slack_cfg.get('channel')

    payload = {
        'username': slack_username,
        'text': msg,
        'channel': slack_channel,
    }

    data = json.dumps(payload)
    headers = {'Content-Type': 'application/json'}
    request = urllib2.Request(slack_url, data, headers=headers)
    return urllib2.urlopen(request).read()
