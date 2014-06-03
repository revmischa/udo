# Handy common utilities for udo modules

import config
import boto

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
