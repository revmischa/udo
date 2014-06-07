import config
import util

from boto.vpc import VPCConnection

_cfg = config.Config()

# class method
def list():
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
    args = util.connection_args()
    return VPCConnection(**args)

def get_vpc_by_name(name):
    vpcs = vpc_conn().get_all_vpcs()
    ret = None
    for vpc in vpcs:
        tags = vpc.tags
        if 'Name' not in tags:
            continue
        vpc_name = tags.get('Name')
        if vpc_name == name:
            # duplicate?
            if ret:
                print "Warning: found more than one VPC with the name {}".format(name)
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
    def activate(self):
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



