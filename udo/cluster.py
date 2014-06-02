import config
import util

from boto.vpc import VPCConnection

_cfg = config.load()

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

class Cluster:
    def __init__(self, name):    
        if name not in _cfg.get('clusters'):
            print "Invalid cluster name: {}".format(name)
            return
        self.cluster_config = _cfg.get('clusters', name)
        self.name = name
        self.conn = vpc_conn()

    def _get_vpc_by_name(self, name):
        vpcs = self.conn.get_all_vpcs()
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

    def status(self):
        vpc = self._get_vpc_by_name(self.name)
        if not vpc:
            return { 'exists': False }

        return {
            'exists': True,
            'state': vpc.state,
            'id': vpc.id
        }
        

