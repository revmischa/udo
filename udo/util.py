# Handy common utilities for udo modules

import config
import boto
import json
import urllib2

_cfg = config.Config()

def region():
    return _cfg.get('region')

# returns dict of arguments common to any boto connection we establish
def connection_args():
    _region = region()
    if not _region:
        # use the default region, I guess?
        print "Warning: default region is not configured"
        return "us-east-1"

    return {
        'region': boto.ec2.get_region(_region)
    }

def message_integrations(msg):
    message_slack(msg)

def message_slack(msg):
    slack_cfg = _cfg.new_root('slack')
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
