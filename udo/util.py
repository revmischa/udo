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

def get_role_config(cluster_name, role_name):
    # check clusters
    cluster_config = _cfg.new_root('clusters')
    if cluster_name not in cluster_config.get():
        print "Invalid cluster name: {}".format(cluster_name)
        return

    # check roles
    roles_config = cluster_config.new_root(cluster_name, 'roles')
    if not roles_config:
        print "No roles defined in cluster {}".format(cluster_name)
        return
    if role_name not in roles_config.get():
        print "Invalid role name: {}".format(role_name)
        return;

    return roles_config.get(role_name)

