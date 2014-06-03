import yaml
from pprint import pprint

"""
This class provides an interface into the entire AWS configuration.
It does more than simply convert a config file into a python data structure;
when you request a key, it will merge all values it finds downwards from the
root, using values defined at the root as defaults.
In addition, hashes and arrays are combined as it merges down.

If this is unclear, take a look at test_config.py and config.sample.yml. 

how2use:
    cfg = Config()

    # get a root configuration value
    region = cfg.get('region')

    # get a role config object
    role_cfg = cfg.new_root('clusters', 'prod', 'roles', 'webapp')
    
    # really queries clusters.prod.roles.webapp.packages, merging any packages 
    # array values it finds along the way
    role_cfg.get('packages')  
""" 

# class method
def load():
    _path = "config.sample.yml"
    f = open(_path, 'r')
    contents = f.read()
    f.close()
    return parse(contents)


# given a YAML string, parse it into a python data structure
def parse(config_yaml):
    return yaml.load(config_yaml)

class Config:
    _root = None
    _path = None

    def __init__(self, root=None):
        if root:
            self._root = root
        else:
            self._root = load()

    def clone(self):
        return Config(self._root)

    # returns a new Config with its base path set to *base
    def new_root(self, *base):
        new_cfg = self.clone()
        if self._path:
            base = self._path + base
        new_cfg._path = base
        return new_cfg

    # get value at current path root
    def get_root(self):
        return self.get()

    def get(self, *path):
        if self._path:
            path = self._path + path
            # print "Current path is: {}".format(path)

        cfg = self._root

        # no path specified? return root
        if len(path) == 0:
            return cfg

        # if path is only one segment, just return whatever is there
        # if len(path) == 1:
        #     return cfg.get(path[0])

        # perform merge from root to leaf node
        key = path[-1]  # get last element, this is what we're merging at all levels

        # iterate downwards, merging all values we find
        cur_val = None

        # start at root level
        cur_level = cfg

        cur_level_key = 'root'
        for level in path:
            if not cur_level:
                # dead end traversing downwards. go with whatever we found last
                print "Warning: {} is not defined in configuration at {}".format(key, level)
                return cur_val

            if key in cur_level:
                cur_val = self.merge(cur_val, cur_level.get(key))
                # print "Found {} in level {}".format(key, cur_level_key)
            
            # go one level deeper
            cur_level = cur_level.get(level)
            cur_level_key = level

        return cur_val

    # returns combination of val1+val2:
    # if val1 or val2 is None, returns whichever is not None
    # if val1 and val2 are lists, returns a combined list
    # if val1 and val2 are dict, returns a combined dict
    # if val1 and val2 are different non-None types, explodes
    # should this be recurse? not sure
    def merge(self, val1, val2):
        if val1 is None:
            return val2
        if val2 is None:
            return val1

        if val1.__class__ is not val2.__class__:
            print "{} is not the same type as {}".format(val1.__class__, val2.__class__)
            return val1

        if val1.__class__ is list:
            # merge lists
            return (val1 + val2)

        if val1.__class__ is dict:
            # merge dicts
            merged = dict(val1.items() + val2.items())
            return merged

        # assume scalar, val2 overwrites val1
        return val2
