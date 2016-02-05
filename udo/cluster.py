"""
# Note: this is not used anymore.

import boto3
import sys
from pprint import pprint

import config
import util

from util import debug

_cfg = config.Config()

# class method
def list():
    debug("In cluster.py class method list")
    clusters = _cfg.get('clusters')
    cluster_names = clusters.keys()
    cluster_names.sort()
    print "Defined clusters:"
    for cluster_name in cluster_names:
        cluster = Cluster(cluster_name)
        status = cluster.status()
        print "    {}:".format(cluster_name)
        for k,v in status.items():
            print "        {}: {}".format(k, v)

def vpc_conn():
    debug("In cluster.py class method vpc_conn")
    ec2 = boto3.resource('ec2')
    vpc_iterator = ec2.vpcs.all()
    return vpc_iterator

def get_vpc_by_name(name):
    debug("In cluster.py class method get_vpc_by_name")
    # TODO: error if more than one vpc has the same Name tag
    vpcs_iterator = vpc_conn() # iterator of all vpcs

    ret = None
    for vpc in vpcs_iterator:
        tags = vpc.tags
        for tag in tags:
             if tag['Key'] == "Name":
                 if tag['Value'] == name:
                     ret = vpc
    return ret

class Cluster:
    def __init__(self, name):    
        if name not in _cfg.get('clusters'):
            print "Invalid cluster name: {}".format(name)
            return
        self.cluster_config = _cfg.get('clusters', name)
        self.name = name
        self.conn = vpc_conn()

    def status(self):
        debug("In cluster.py status")
        vpc = get_vpc_by_name(self.name)
        if not vpc:
            return { 'exists': False }

        # check if this VPC is managed by udo
        tags = vpc.tags
        vpc_is_managed = False
        if 'Udo' in tags:
            vpc_is_managed = True

        return {
            'udo': vpc_is_managed,
            'exists': True,
            'state': vpc.state,
            'id': vpc.id
        }
    
    # active this cluster
    #
    # NOTE: this might not work right
    # We might get rid of cluster.py completely
    def activate(self):
        debug("In cluster.py activate")
        conn = vpc_conn()

        cfg = _cfg.get('clusters', self.name)
        if not cfg:
            print "No configuration found for {}".format(self.name)
            return False

        vpc = get_vpc_by_name(self.name)
        if vpc:
            print "Cluster {} already exists".format(self.name)
            return

        # create VPC
        #
        # boto3 docs example for creating a vpc:
        # ec2 = boto3.resource('ec2')
        # vpc = ec2.create_vpc(CidrBlock='10.0.0.0/24')
        # subnet = vpc.create_subnet(CidrBlock='10.0.0.0/25')
        # gateway = ec2.create_internet_gateway()
 
        subnet_cidr = cfg.get('subnet_cidr')
        if not subnet_cidr:
            print "No subnet definition found for {}".format(self.name)
            return False
        vpc = conn.create_vpc(subnet_cidr)
        vpc.add_tag('Name', value=self.name)
        # for now assume that our subnet is the same CIDR as the VPC
        # this is simpler but less fancy
        subnet = conn.create_subnet(vpc.id, subnet_cidr)
        # all done
        util.message_integrations("Created VPC {}".format(self.name))

        # mark that this cluster is being managed by udo
        vpc.add_tag('udo', value=True)

        return True

"""
