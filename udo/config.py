import yaml

class Config:
    _cfg = None

    def load(self):
        self.parse("a: 1")

    # given a YAML string, parse it into a python data structure
    def parse(self, config_yaml):
        self._cfg = yaml.load(config_yaml)
        return self._cfg

    def get(self, *path):
        if len(path) == 0:
            raise Error("config.get requires a key path")
            return

        # make sure config is loaded
        if not self._cfg:
            self.load()

        cfg = self._cfg

        # if path is only one segment, just return whatever is there
        if len(path) == 1:
            return cfg.get(path[0])

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
                print "Warning: {} is not defined in configuration at {}".format(level, level)
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
