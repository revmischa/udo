import config

_cfg = config.load()

# class method
def list():
    clusters = _cfg.get('clusters')
    cluster_names = clusters.keys()
    cluster_names.sort()
    print "Defined clusters: {}".format(cluster_names)

class Cluster:
    def init(self, name):    
        if name not in _cfg:
            print "Invalid cluster name: {}".format(name)
            return
        self.cluster_config = _cfg.get('clusters', name)

